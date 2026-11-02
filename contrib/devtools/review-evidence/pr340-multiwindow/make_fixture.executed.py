#!/usr/bin/env python3
"""Extend the recorded disposable #340 fixture to 1024 historical RC bodies."""
from pathlib import Path
import json, sys, shutil, os, hashlib
ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'toolchain-2026-10-31/source'
sys.path.insert(0, str(SOURCE / 'test/functional'))
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import assert_equal

class Fixture(BitcoinTestFramework):
    def set_test_params(self):
        self.num_nodes = 1
        self.setup_clean_chain = True
        self.rpc_timeout = 60
        self.extra_args = [[ '-modelnet=0', '-connect=0', '-dbcache=16',
            '-matmulvalidation=consensus', '-matmulrcexecution=strict-device',
            '-matmulrcconfirmcpu=0', '-assumevalid=0', '-checkblockindex=1',
            '-retainshieldedcommitmentindex=0', '-matmulattestationserve=0']]

    def setup_network(self):
        self.add_nodes(1, self.extra_args)
        dest = self.nodes[0].chain_path
        shutil.copytree(ROOT.parent / 'pr340-pinned-metal/fixture-run/node0/regtest', dest, dirs_exist_ok=True,
            ignore=shutil.ignore_patterns('debug.log', '.cookie', 'btxd.pid', 'pinned-window1124.dat'))
        self.start_nodes()

    def run_test(self):
        node = self.nodes[0]
        assert_equal(node.getblockcount(), 1124)
        assert_equal(node.getbestblockhash(), '7c52a35fdde44917072c7e20e228fe1c64c0b037e59d1b353ff8f2479dc94626')
        node.setmocktime(node.getblockheader(node.getbestblockhash())['time'])
        while node.getblockcount() < 4196:
            self.generate(node, min(25, 4196-node.getblockcount()), sync_fun=self.no_op)
            self.log.info('fixture height=%d', node.getblockcount())
        dump = node.dumptxoutset('pinned-window4196.dat', 'latest')
        runtime = node.getmininginfo()['backend_runtime']['rc_exact_replay']['last_validation']
        assert runtime['full_metal_pipeline'] and runtime['execution_policy'] == 'strict-device', runtime
        for k in ['cpu_gemm_calls', 'cpu_gemm_fallbacks', 'device_xof_fallbacks', 'host_xof_calls']:
            assert_equal(runtime[k], 0)
        result = {'snapshot':dump, 'snapshot_file_sha256':hashlib.sha256(Path(dump['path']).read_bytes()).hexdigest(),
            'seed_fixture':'Existing recorded regtest299 fixture; blocks300-1124 generated on strict-device M4 Metal.',
            'seed_binary_sha256':hashlib.sha256(Path(os.environ['BTXD']).read_bytes()).hexdigest(),
            'runtime':runtime}
        (ROOT/'fixture.json').write_text(json.dumps(result, indent=2, default=str))
        self.log.info('snapshot1124 saved,1024 RC bodies above legacy prefix100')

if __name__ == '__main__':
    Fixture(__file__).main()
