"""Import and construct the actual framework/fixture; forbid process/socket starts."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,sys,tempfile
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,default=root/'framework-source')
parser.add_argument('--fixture',type=Path,default=root/'fixture/wallet_active_pair_recovery.py')
parser.add_argument('--build-root',type=Path,default=root)
parser.add_argument('--output',type=Path,default=root/'preparation/framework-preflight.json')
args=parser.parse_args()
framework=args.source.resolve();fixture=args.fixture.resolve()
args.output.parent.mkdir(parents=True,exist_ok=True)
events=[]
def audit(event,args):
    if event in {'subprocess.Popen','os.system','os.posix_spawn','socket.__new__','os.fork','os.forkpty'}:
        events.append(event)
        raise RuntimeError('External execution/socket forbidden in constructor preflight')
sys.addaudithook(audit)
sys.path.insert(0,str(framework/'test/functional'))
spec=importlib.util.spec_from_file_location('wallet_active_pair_fixture_preflight',fixture)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
with tempfile.TemporaryDirectory(prefix='framework-construction-',dir=args.output.parent)as temp:
    config=Path(temp)/'config.ini'
    config.write_text('[environment]\nCLIENT_NAME=BTX\nCLIENT_BUGREPORT=not-used\nSRCDIR='+str(framework)+'\nBUILDDIR='+str(args.build_root.resolve())+'\nEXEEXT=\nRPCAUTH=not-used\n[components]\nENABLE_WALLET=true\nUSE_SQLITE=true\nUSE_BDB=false\nENABLE_CLI=true\nENABLE_BITCOIND=true\nENABLE_MODELNET=false\nENABLE_ZMQ=false\nENABLE_EXTERNAL_SIGNER=false\n')
    sys.argv=[str(fixture),'--configfile='+str(config),'--descriptors','--timeout-factor=1','--portseed=917']
    case=module.ActivePairRecoveryTest(str(fixture))
    assert case.num_nodes==2 and case.setup_clean_chain and case.wallet_names==[False,False]
    assert case.nodes==[] and case.network_thread is None
    assert case.options.descriptors is True and case.is_wallet_compiled() and case.is_sqlite_compiled()
    for name in ['generatetoaddress','sync_mempools','sync_blocks','skip_if_no_wallet','skip_if_no_sqlite']:
        assert callable(getattr(case,name)),name
    case.skip_test_if_missing_module()
    assert case._requires_wallet
    class NoImplicitWalletRPC:
        def __getattr__(self, name):
            raise AssertionError('Implicit wallet access forbidden in no-wallet mode')
    case.nodes = [NoImplicitWalletRPC(), NoImplicitWalletRPC()]
    case.import_deterministic_coinbase_privkeys()
    case.nodes = []
    assert not events
result={'status':'PASS_CONSTRUCTION_ONLY','python':sys.version.split()[0],'fixture_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),'framework_source':'f9ba112822c0089ae2fc3bb5f71e1a28c7cf0302','nodes_constructed':0,'network_threads_started':0,'forbidden_events':events,'main_setup_run_test_called':False,'rpc_called':False,'wallet_init_path':'real import_deterministic_coinbase_privkeys/init_wallet; two RPC-tripwire placeholders; no calls'}
args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
