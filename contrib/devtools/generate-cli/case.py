"""Observe actual CLI -> btxd -> real helper, with an explicitly fake generate adapter."""
from pathlib import Path
import hashlib
from decimal import Decimal
import json
import os
import socket
import struct
import subprocess
import time

from test_framework.test_framework import BitcoinTestFramework
from test_framework.authproxy import JSONRPCException


def record_decimal(value):
    # AuthServiceProxy retains fractional JSON numbers as Decimal. Preserve the
    # exact text and type in diagnostic records; do not round financial data.
    if isinstance(value, Decimal):
        return {'decimal': str(value)}
    raise TypeError('Unsupported observation value: ' + type(value).__name__)


class GenerateCliObservation(BitcoinTestFramework):
    def set_test_params(self):
        self.num_nodes = 1
        self.setup_clean_chain = True
        self.root = Path(os.environ['GENERATE_RUNTIME'])
        self.sock = self.root / 'helper.sock'
        self.extra_args = [['-disablewallet', '-modelnet=0', '-modelbind=off',
                            '-modelrpcsocket=' + str(self.sock),
                            '-dnsseed=0', '-discover=0', '-networkactive=0']]

    def run_test(self):
        out = Path(os.environ['GENERATE_RESULTS'])
        build = Path(self.config['environment']['BUILDDIR'])
        records = {'scope': 'Actual unchanged CLI, node and helper; synthetic model and fake local generation adapter. No real model inference.',
                   'cli': [], 'raw': [], 'adapter_requests': []}
        observations = out / 'observations.json'
        adapter_log = self.root / 'adapter.jsonl'
        adapter = self.root / 'fake-generate'
        adapter.write_text('#!/usr/bin/env python3\n'
            'import json,sys\n'
            'from pathlib import Path\n'
            'request=json.loads(sys.stdin.readline())\n'
            'with Path(__file__).with_name("adapter.jsonl").open("a") as f: f.write(json.dumps(request)+"\\n")\n'
            'print(json.dumps({"ok":True,"generated":True,"text":"echo:"+request["prompt"],"backend":"fake"}),flush=True)\n')
        adapter.chmod(0o700)
        source = self.root / 'tiny-model'
        source.mkdir()
        header = b'{"__metadata__":{"t":"147"}}'
        (source / 'model.safetensors').write_bytes(struct.pack('<Q', len(header)) + header)
        (source / 'config.json').write_text('{"architectures":["LlamaForCausalLM"],"model_type":"llama"}\n')
        helper_args = [str(build / 'bin/btx-modeld'), '-modeldir=' + str(self.root / 'catalog'),
                       '-modelrpcsocket=' + str(self.sock), '-modelstorage=16MiB',
                       '-modelhost=0', '-modelseed=off', '-modelfollowpeers=0',
                       '-modellandiscovery=0', '-modelnatpmp=0', '-pwcchain=regtest']
        env = dict(os.environ, BTX_MODEL_GENERATE=str(adapter))
        env.pop('BTX_LLAMA_CLI', None)
        env.pop('BTX_EXL3_CLI', None)
        records['helper_args'] = helper_args
        helper = None
        helper_stream = (out / 'helper.log').open('wb')
        try:
            helper = subprocess.Popen(helper_args, cwd=self.root, env=env,
                                      stdout=helper_stream, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + 30
            while True:
                assert helper.poll() is None, 'Owned helper exited at startup'
                try:
                    info = self.nodes[0].getmodelnetworkinfo()
                    if info.get('helper_ready'):
                        records['helper_ready'] = info
                        break
                except JSONRPCException:
                    pass
                assert time.monotonic() < deadline, 'Helper readiness deadline'
                time.sleep(.1)
            records['node_before'] = self.nodes[0].getblockchaininfo()
            imported = self.nodes[0].hostmodel(str(source), {'pin': True, 'publish': False})
            records['imported'] = imported
            identifier = imported['model_id']
            opts = {'prompt': 'hello-btx', 'max_new_tokens': 8}
            opts_text = json.dumps(opts, separators=(',', ':'))

            def requests():
                return [json.loads(line) for line in adapter_log.read_text().splitlines()] if adapter_log.exists() else []

            def raw(label, value, named=False):
                before = len(requests())
                try:
                    result = (self.nodes[0].generatemodel(id=identifier, opts=value) if named
                              else self.nodes[0].generatemodel(identifier, value))
                    row = {'label': label, 'params': {'id': identifier, 'opts': value} if named else [identifier, value],
                           'result': result, 'error': None}
                except JSONRPCException as error:
                    row = {'label': label, 'value': value, 'error': error.error}
                row['adapter_delta'] = requests()[before:]
                records['raw'].append(row)
                observations.write_text(json.dumps(records, indent=2, default=record_decimal) + '\n')
                return row

            cli_prefix = [str(build / 'bin/btx-cli'), '-regtest',
                          '-datadir=' + str(self.nodes[0].datadir_path),
                          '-conf=' + str(self.nodes[0].bitcoinconf), '-rpcclienttimeout=15']
            cli_control = subprocess.run(cli_prefix + ['getblockchaininfo'], capture_output=True, text=True, timeout=20)
            assert cli_control.returncode == 0, 'CLI must reach the exact disposable node: ' + cli_control.stderr
            assert json.loads(cli_control.stdout)['bestblockhash'] == records['node_before']['bestblockhash']
            records['cli_connection_control'] = {'returncode': 0, 'chain': json.loads(cli_control.stdout)['chain']}

            def cli(label, named=False):
                args = list(cli_prefix)
                args += (['-named', 'generatemodel', 'id=' + identifier, 'opts=' + opts_text] if named
                         else ['generatemodel', identifier, opts_text])
                before = len(requests())
                completed = subprocess.run(args, capture_output=True, text=True, timeout=20)
                row = {'label': label, 'args': args, 'returncode': completed.returncode,
                       'stdout': completed.stdout, 'stderr': completed.stderr,
                       'adapter_delta': requests()[before:]}
                records['cli'].append(row)
                observations.write_text(json.dumps(records, indent=2, default=record_decimal) + '\n')
                return row

            for label, named in [('raw-object-positional', False), ('raw-object-named', True)]:
                control = raw(label, opts, named)
                assert control['error'] is None, 'Valid object control must reach real helper'
                assert control['result']['text'] == 'echo:hello-btx'
                assert control['result']['backend'] == 'fake'
                assert control['result']['generated'] is True
                assert control['result']['automatic_spend_atoms'] == 0
                assert control['result']['remote_inference'] is False
                assert control['result']['network_server'] is False
                assert len(control['adapter_delta']) == 1
                assert control['adapter_delta'][0]['prompt'] == opts['prompt']
                assert control['adapter_delta'][0]['max_new_tokens'] == 8

            cli('documented-positional')
            cli('documented-named', True)
            raw('raw-string-observation', opts_text)
            # A final legitimate request proves the diagnostic did not wedge the helper.
            after = raw('raw-object-after-cli', opts)
            assert after['error'] is None and after['result']['text'] == 'echo:hello-btx'
            records['node_after'] = self.nodes[0].getblockchaininfo()
            assert records['node_before']['bestblockhash'] == records['node_after']['bestblockhash']
            assert records['node_after']['blocks'] == 0
            try:
                self.nodes[0].listwallets()
                raise AssertionError('Wallet RPC unexpectedly available with -disablewallet')
            except JSONRPCException as error:
                assert error.error['code'] == -32601
                records['wallet_rpc_disabled'] = error.error
            records['adapter_requests'] = requests()
            records['outcome'] = 'Valid object controls passed; CLI observations collected without assuming their failure mechanism.'
            self.log.info('Real node/helper object controls passed; both CLI outcomes recorded; node responsive at genesis')
        finally:
            if helper is not None:
                if helper.poll() is None:
                    helper.terminate()
                helper.wait(timeout=20)
                records['helper_returncode'] = helper.returncode
            helper_stream.close()
            records['adapter_requests'] = [json.loads(line) for line in adapter_log.read_text().splitlines()] if adapter_log.exists() else []
            records['helper_socket_after_stop'] = self.sock.exists()
            observations.write_text(json.dumps(records, indent=2, default=record_decimal) + '\n')


if __name__ == '__main__':
    GenerateCliObservation(__file__).main()
