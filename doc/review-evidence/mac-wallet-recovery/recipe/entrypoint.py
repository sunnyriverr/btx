"""Future constructor-only fixture preflight; never calls main/setup or starts nodes."""
from pathlib import Path
import json
import runpy
import sys

fixture, config, tmpdir, portseed = sys.argv[1:]
fixture = Path(fixture).resolve()
sys.path.insert(0, str(fixture.parent))
sys.argv = [str(fixture), '--configfile=' + config, '--tmpdir=' + tmpdir,
            '--portseed=' + portseed, '--nocleanup']
module = runpy.run_path(str(fixture), run_name='source_preflight')
test = module['EncryptedBackupRecoveryTest'](str(fixture))
assert test.chain == 'regtest' and test.setup_clean_chain and test.num_nodes == 1
assert test.nodes == [] and test.network_thread is None and test.bind_to_localhost_only
assert test.options.configfile == config and test.options.port_seed == int(portseed)
assert not Path(tmpdir).exists()
assert test.config['components'].getboolean('ENABLE_WALLET')
assert test.config['components'].getboolean('USE_SQLITE')
assert '-swapnet=0' in test.extra_args[0] and '-connect=0' in test.extra_args[0]
print(json.dumps({'constructed': True, 'main_or_setup_called': False,
                  'nodes_started': False, 'chain': test.chain,
                  'num_nodes': test.num_nodes, 'loopback_default': test.bind_to_localhost_only}))
