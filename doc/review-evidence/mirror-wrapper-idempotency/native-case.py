from pathlib import Path
import hashlib,importlib.util,inspect,json,os,subprocess,time
from test_framework.test_framework import BitcoinTestFramework
from test_framework.authproxy import JSONRPCException
W=Path(os.environ['GITHUB_WORKSPACE']);HERE=Path(__file__).parent;O=W/'rpc-help-live-results';variant=os.environ['MIRROR_VARIANT']
spec=importlib.util.spec_from_file_location('maintained_mirror_case',HERE/'candidate-test.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);cls=module.SwarmProfileOverridesTest
method=cls.test_mirror_cli
records={'variant':variant,'method_sha256':hashlib.sha256(inspect.getsource(method).encode()).hexdigest(),'wrapper_calls':[],'helper_calls':[],'method_pass':False}
original_run=subprocess.run
def observe_run(args,*a,**k):
 result=original_run(args,*a,**k)
 if any(str(x).endswith('/btx-model') for x in args):records['wrapper_calls'].append({'args':[str(x) for x in args],'exit':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
 return result
module.subprocess.run=observe_run
old_helper=cls.helper
def helper(self,method,params):
 result=old_helper(self,method,params);records['helper_calls'].append({'method':method,'params':params,'result':result});return result
cls.helper=helper

def params(self):
 self.num_nodes=1;self.setup_clean_chain=True;self.root=W/'rpc-help-live-runtime'/variant;self.root.mkdir();self.modeldir=self.root/'catalog';self.modeldir.mkdir();self.socket_path=self.root/'helper.sock'
 self.extra_args=[['-disablewallet','-modelnet=0','-modelbind=off','-modelrpcsocket='+str(self.socket_path),'-dnsseed=0','-discover=0','-networkactive=0']]
cls.set_test_params=params;cls.setup_nodes=BitcoinTestFramework.setup_nodes

def focused(self):
 build=Path(self.config['environment']['BUILDDIR']);stream=(O/(variant+'-helper.log')).open('wb');proc=None
 try:
  args=[str(build/'bin/btx-modeld'),'-modeldir='+str(self.modeldir),'-modelrpcsocket='+str(self.socket_path),'-modelstorage=16MiB','-modelhost=0','-modelseed=off','-modelfollowpeers=0','-modellandiscovery=0','-modelnatpmp=0','-pwcchain=regtest']
  proc=subprocess.Popen(args,stdout=stream,stderr=subprocess.STDOUT);self.ready();method(self);records['method_pass']=True
 except Exception as e:records['error']=str(e);raise
 finally:
  try:
   if proc is not None:
    if proc.poll() is None:proc.terminate()
    proc.wait(timeout=20);records['helper_exit']=proc.returncode
  finally:
   stream.close();self.stop_nodes();records['node_stopped']=True;records['socket_remaining']=self.socket_path.exists()
   file=self.modeldir/'mirror.json'
   if file.exists():records['saved_mirror']=json.loads(file.read_text())
   (O/(variant+'-observations.json')).write_text(json.dumps(records,indent=2))
cls.run_test=focused
cls(__file__).main()
