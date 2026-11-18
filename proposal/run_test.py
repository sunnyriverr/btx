"""Run the identical maintained test with explicit isolated native-node policy."""
from pathlib import Path
import os,sys,runpy
w=Path(os.environ['GITHUB_WORKSPACE']);phase=sys.argv[1];assert phase in ['baseline','candidate']
script=w/'product/test/functional/wallet_modelnet_funding.py';sys.path.insert(0,str(script.parent));ns=runpy.run_path(str(script),run_name='funding_fixture')
Test=ns['ModelnetFundingTest'];original=Test.set_test_params
def params(self):
 original(self)
 self.extra_args[0].extend(['-modelnet=0','-swapnet=0','-rpcdoccheck=1','-dbcache=16','-par=1'])
Test.set_test_params=params
binary=w/('baseline/btxd'if phase=='baseline'else'gui-pilot-runtime/qtbuild/bin/btxd');os.environ['BTXD']=str(binary);os.environ['BTXCLI']=str(w/'gui-pilot-runtime/qtbuild/bin/btx-cli')
sys.argv=[str(script),'--configfile='+str(w/'gui-pilot-runtime/qtbuild/test/config.ini'),'--tmpdir='+str(w/('runtime-'+phase)),'--descriptors','--nocleanup']
Test(str(script)).main()
