"""Actual unchanged node/helper/CLI labels; disposable identity-only state."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
from test_framework.test_framework import BitcoinTestFramework


class IdentityLabelWorkflow(BitcoinTestFramework):
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
        prefix = [str(package / 'bin/btx-cli'), '-regtest', '-datadir=' + str(node.datadir_path),
                  '-conf=' + str(node.bitcoinconf), '-rpcclienttimeout=15']
        record = {'bad_cli': [], 'quoted_controls': [], 'controls': [], 'observation_complete': False}
        helper = None
        log = (out / 'helper.log').open('wb')

        def save():
            (out / 'observations.json').write_text(json.dumps(record, indent=2) + '\n')

        def control(name, passed):
            record['controls'].append({'name': name, 'passed': bool(passed)})
            save()
            assert passed, name

        def snapshot():
            listed = node.listmodelidentities()['identities']
            files = list(cat.rglob('identities.json'))
            assert len(files) == 1
            public = json.loads(files[0].read_text())['identities']
            assert listed == public
            return {'identities': listed, 'sha256': hashlib.sha256(files[0].read_bytes()).hexdigest(),
                    'mtime_ns': files[0].stat().st_mtime_ns}

        def persisted(result, label, before_count):
            after = snapshot()
            return (type(result.get('label')) is str and result['label'] == label and
                    len(after['identities']) == before_count + 1 and
                    any(row['id'] == result['id'] and row['label'] == label for row in after['identities']) and
                    result.get('wallet_backed') is False and result.get('contains_wallet_material') is False and
                    Path(result['secret_path']).resolve().is_relative_to(self.root.resolve()))

        def cli(raw, named):
            args = prefix + (['-named'] if named else []) + ['createmodelidentity', 'label=' + raw if named else raw]
            result = subprocess.run(args, capture_output=True, text=True, timeout=25)
            return {'raw': raw, 'named': named, 'returncode': result.returncode,
                    'stdout': result.stdout, 'stderr': result.stderr}

        try:
            helper_args = [str(package / 'bin/btx-modeld'), '-modeldir=' + str(cat),
                           '-modelrpcsocket=' + str(self.sock), '-modelstorage=16MiB',
                           '-modelhost=0', '-modelseed=off', '-modelfollowpeers=0',
                           '-modellandiscovery=0', '-modelnatpmp=0', '-pwcchain=regtest']
            helper = subprocess.Popen(helper_args, stdout=log, stderr=subprocess.STDOUT)
            self.wait_until(lambda: node.getmodelnetworkinfo().get('helper_ready') is True, timeout=40)
            args = Path('/proc/' + str(node.process.pid) + '/cmdline').read_bytes().decode().split('\0')
            control('live node remains disposable/offline/wallet-disabled',
                    all(flag in args for flag in self.extra_args[0]))
            info = node.getmodelnetworkinfo()
            control('default research identity ready without labelled CLI', info.get('identity_ready') is True and
                    info.get('identity_wallet_key') is False)
            record['baseline_identities'] = len(snapshot()['identities'])
            for direct_named in [False, True]:
                before = snapshot()
                label = 'direct named RPC label' if direct_named else 'direct RPC label'
                result = node.createmodelidentity(label=label) if direct_named else node.createmodelidentity(label)
                control('direct string RPC creates and persists exact label ' + str(direct_named),
                        persisted(result, label, len(before['identities'])))
            for named in [False, True]:
                for label in ['sunny-label', 'true']:
                    before = snapshot()
                    refused = cli(label, named)
                    refused['state_unchanged'] = snapshot() == before
                    record['bad_cli'].append(refused)
                    save()
                    control('bare label refused and preserves identity state ' + str((named, label)),
                            refused['returncode'] != 0 and refused['state_unchanged'])
                    if label == 'sunny-label':
                        control('bare text fails client JSON parsing ' + str(named),
                                'Error parsing JSON' in refused['stderr'])
                        refused['failure_stage'] = 'client JSON parsing, before RPC'
                    else:
                        control('Boolean-looking text reaches node as wrong type ' + str(named),
                                'error code: -3' in refused['stderr'] and 'type string' in refused['stderr'])
                        refused['failure_stage'] = 'node RPC argument type check, before helper'
                    accepted = cli(json.dumps(label), named)
                    accepted['requested_literal'] = label
                    accepted['persisted_exactly'] = accepted['returncode'] == 0 and persisted(
                        json.loads(accepted['stdout']), label, len(before['identities']))
                    record['quoted_controls'].append(accepted)
                    control('JSON-quoted workaround preserves exact label ' + str((named, label)),
                            accepted['persisted_exactly'])
            before = snapshot()
            result = node.createmodelidentity()
            control('no-label default workflow remains supported', persisted(result, '', len(before['identities'])))
            info = node.getmodelnetworkinfo()
            control('helper stays ready after failures and controls', info.get('helper_ready') is True)
            control('zero height, peers and automatic spend', node.getblockcount() == 0 and
                    node.getconnectioncount() == 0 and info['automatic_spend_atoms'] == 0)
            record['final_identity_count'] = len(snapshot()['identities'])
            control('only direct/quoted/no-label controls create identities',
                    record['final_identity_count'] == record['baseline_identities'] + 7)
            record['controls_complete'] = True
            record['observation_complete'] = True
            save()
        finally:
            try:
                if helper is not None:
                    if helper.poll() is None:
                        helper.terminate()
                    helper.wait(timeout=20)
                    record['helper_returncode'] = helper.returncode
            finally:
                log.close()
                self.stop_nodes()
                record['node_rpc_shutdown_complete'] = True
                record['helper_socket_after_stop'] = self.sock.exists()
                save()


if __name__ == '__main__':
    IdentityLabelWorkflow(__file__).main()
