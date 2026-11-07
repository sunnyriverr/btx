"""Same desired literal-label workflow against baseline and candidate CLIs."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
from test_framework.test_framework import BitcoinTestFramework

LABELS = ['sunny-label', 'true', '123', 'null', '{"team":"btx"}', '[1,2]',
          '"quoted"', '', 'sunny river=名']


class IdentityLabels(BitcoinTestFramework):
    def set_test_params(self):
        self.num_nodes = 1
        self.setup_clean_chain = True
        self.bind_to_localhost_only = True
        self.root = Path(os.environ['IDENTITY_RUNTIME'])
        self.sock = self.root / 'helper.sock'
        self.extra_args = [['-disablewallet', '-modelnet=0', '-modelbind=off',
                            '-modelrpcsocket=' + str(self.sock), '-connect=0',
                            '-dnsseed=0', '-discover=0', '-networkactive=0']]

    def run_test(self):
        out = Path(os.environ['IDENTITY_RESULTS'])
        package = Path(self.config['environment']['BUILDDIR'])
        cat = self.root / 'catalog'
        cat.mkdir()
        node = self.nodes[0]
        prefix = [os.environ['IDENTITY_CLI_BINARY'], '-regtest', '-datadir=' + str(node.datadir_path),
                  '-conf=' + str(node.bitcoinconf), '-rpcclienttimeout=15']
        record = {'cli': [], 'direct': [], 'controls': [], 'requirements': []}
        helper = None
        stream = (out / 'helper.log').open('wb')

        def save():
            (out / 'observations.json').write_text(json.dumps(record, indent=2) + '\n')

        def control(name, value):
            record['controls'].append({'name': name, 'passed': bool(value)})
            save()
            assert value, name

        def snapshot():
            listed = node.listmodelidentities()['identities']
            paths = list(cat.rglob('identities.json'))
            assert len(paths) == 1
            data = paths[0].read_bytes()
            assert json.loads(data)['identities'] == listed
            return {'count': len(listed), 'sha256': hashlib.sha256(data).hexdigest(),
                    'mtime_ns': paths[0].stat().st_mtime_ns}, listed

        def stored(response, label, before):
            after, listed = snapshot()
            passed = (after['count'] == before['count'] + 1 and type(response.get('label')) is str and
                      response['label'] == label and any(x['id'] == response['id'] and x['label'] == label for x in listed) and
                      response.get('wallet_backed') is False and response.get('contains_wallet_material') is False and
                      Path(response['secret_path']).resolve().is_relative_to(self.root.resolve()))
            return after, passed

        try:
            helper = subprocess.Popen([
                str(package / 'bin/btx-modeld'), '-modeldir=' + str(cat),
                '-modelrpcsocket=' + str(self.sock), '-modelstorage=16MiB', '-modelhost=0',
                '-modelseed=off', '-modelfollowpeers=0', '-modellandiscovery=0',
                '-modelnatpmp=0', '-pwcchain=regtest',
            ], stdout=stream, stderr=subprocess.STDOUT)
            self.wait_until(lambda: node.getmodelnetworkinfo().get('helper_ready') is True, timeout=40)
            args = Path('/proc/' + str(node.process.pid) + '/cmdline').read_bytes().decode().split('\0')
            control('live offline/wallet-disabled node policy', all(flag in args for flag in self.extra_args[0]))
            info = node.getmodelnetworkinfo()
            control('default research identity ready', info.get('identity_ready') is True and
                    info.get('identity_wallet_key') is False)
            initial, _ = snapshot()
            record['initial'] = initial
            for named in [False, True]:
                before, _ = snapshot()
                label = 'direct named control' if named else 'direct positional control'
                response = node.createmodelidentity(label=label) if named else node.createmodelidentity(label)
                after, passed = stored(response, label, before)
                record['direct'].append({'named': named, 'label': label, 'returned_label': response.get('label'),
                                          'before': before, 'after': after, 'persisted_exactly': passed})
                control('direct string RPC control ' + str(named), passed)
            for named in [False, True]:
                for label in LABELS + [None]:
                    before, _ = snapshot()
                    command = prefix + (['-named'] if named else []) + ['createmodelidentity']
                    if label is not None:
                        command.append('label=' + label if named else label)
                    result = subprocess.run(command, capture_output=True, text=True, timeout=25)
                    row = {'named': named, 'literal_argument': label, 'returncode': result.returncode,
                           'stderr': result.stderr, 'stdout_sha256': hashlib.sha256(result.stdout.encode()).hexdigest(),
                           'before': before}
                    if result.returncode == 0:
                        response = json.loads(result.stdout)
                        after, consistent = stored(response, response.get('label'), before)
                        row.update(after=after, returned_label=response.get('label'), public_id=response.get('id'))
                        control('accepted CLI response matches persisted identity ' + str(len(record['cli'])), consistent)
                        passed = consistent and response['label'] == (label if label is not None else '')
                    else:
                        after, _ = snapshot()
                        row['after'] = after
                        control('refused CLI preserves state ' + str(len(record['cli'])), before == after)
                        passed = False
                    record['cli'].append(row)
                    record['requirements'].append({'name': 'literal label ' + str((named, label)), 'passed': passed})
                    save()
            info = node.getmodelnetworkinfo()
            control('helper remains ready', info.get('helper_ready') is True)
            control('zero height/chain peers/automatic spend', node.getblockcount() == 0 and
                    node.getconnectioncount() == 0 and info['automatic_spend_atoms'] == 0)
            final, _ = snapshot()
            record['final'] = final
            control('exactly one identity per accepted CLI/direct call',
                    final['count'] == initial['count'] + len(record['direct']) +
                    sum(row['returncode'] == 0 for row in record['cli']))
            record['controls_complete'] = True
            record['acceptance_pass'] = all(row['passed'] for row in record['requirements'])
            save()
            assert record['acceptance_pass'], 'Literal identity label requirements failed: ' + str(
                [row['name'] for row in record['requirements'] if not row['passed']])
        finally:
            try:
                if helper is not None:
                    if helper.poll() is None:
                        helper.terminate()
                    helper.wait(timeout=20)
                    record['helper_returncode'] = helper.returncode
            finally:
                stream.close()
                self.stop_nodes()
                record['node_rpc_shutdown_complete'] = True
                save()


if __name__ == '__main__':
    IdentityLabels(__file__).main()
