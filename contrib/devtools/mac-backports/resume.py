"""Finish only focused699 and the unrun698 valid-serving control from saved state."""
from pathlib import Path
import os,json,tarfile,shutil,time,sys,traceback
import run as c
c.EXECUTION_LIMIT=1500
W,S,B,R,F=c.W,c.S,c.B,c.R,c.F
c.STATE.update(previous_run=43647289770,scope='Original target compile/link settings; temporary main+denialofservice source selection. Not a full test_btx build.')

def main():
 assert shutil.disk_usage(W).free>15*1024**3
 _,head=c.cmd(['git','-C',S,'rev-parse','HEAD'],'source');assert head.strip()==c.STATE['base']
 c.cmd(['xcodebuild','-version'],'xcode');_,clang=c.cmd(['xcrun','clang++','--version'],'clang');assert 'Apple clang version 17.0.0' in clang
 _,sdk=c.cmd(['xcrun','--sdk','macosx','--show-sdk-version'],'sdk');assert sdk.strip()=='15.5'
 payload=W/'producer-restore';receipt=json.loads((payload/'receipt.json').read_text());assert receipt['sha256']=='cc75953aedc1941e3ac8e1c0b48244e17328902e3c1c3cccaaaeb2975c912580';assert c.sha(payload/'checkpoint.tar.gz')==receipt['sha256']
 inv=json.loads((payload/'inventory.json').read_text());c.STATE['producer_checkpoint']=receipt;c.save()
 with tarfile.open(payload/'checkpoint.tar.gz') as tar:
  for member in tar:
   if not member.name.startswith('mac-config-build/'):continue
   assert not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
   dest=W/member.name;meta=inv[member.name];assert dest.parent.resolve().is_relative_to(W.resolve())
   if member.isdir():dest.mkdir(parents=True,exist_ok=True);continue
   dest.parent.mkdir(parents=True,exist_ok=True)
   if member.issym():
    assert member.linkname==meta['target'] and (dest.parent/member.linkname).resolve().is_relative_to(W.resolve())
    dest.symlink_to(member.linkname);continue
   assert member.isfile();data=tar.extractfile(member).read();assert __import__('hashlib').sha256(data).hexdigest()==meta['sha256'];dest.write_bytes(data);dest.chmod(meta['mode']);os.utime(dest,ns=(meta['mtime_ns'],meta['mtime_ns']))
 c.apply('tests');c.apply('product')
 matched=0
 for name,meta in inv.items():
  dest=W/name
  if name.startswith('product/') and meta['type']=='file' and dest.is_file() and not dest.is_symlink() and c.sha(dest)==meta['sha256']:
   os.utime(dest,ns=(meta['mtime_ns'],meta['mtime_ns']));matched+=1
 c.STATE['matched_source_mtimes']=matched
 c.cmd(['brew','install','--force-bottle','boost@1.85','libevent','zeromq','libomp','qt','qrencode','librsvg','libicns','python@3.12'],'dependencies',600)
 _,ssl=c.cmd(['brew','--prefix','openssl@3'],'ssl-prefix');ssl=Path(ssl.strip())
 assert c.sha(ssl/'lib/libssl.a')=='b1a96521d10e2ce59ece360814915ed33c0e65aa60f7a9844b8b94c5d048cc56'
 assert c.sha(ssl/'lib/libcrypto.a')=='76304e70825b4522b15461ad29c9106db1eeb8d421a12a641c210dabb11ed375'
 _,py=c.cmd(['brew','--prefix','python@3.12'],'python-prefix');python=Path(py.strip())/'bin/python3.12'
 c.cmd([python,'-m','venv',W/'test-env'],'python-env');c.ENV['TEST_PYTHON']=str(W/'test-env/bin/python');c.cmd([c.ENV['TEST_PYTHON'],'-m','pip','install','cryptography==46.0.4'],'python-crypto',180)
 c.ENV.update(BTX_OPENSSL=str(ssl/'bin/openssl'),PATH=str(W/'test-env/bin')+':'+str(ssl/'bin')+':'+c.ENV['PATH'])
 # A private test-TU selection; no product or assertion change. Preserve original target links, definitions and dependencies.
 cmake=S/'src/test/CMakeLists.txt';overlay='\n# Private699 qualification: retain original fixture and library configuration.\nset_property(TARGET test_btx PROPERTY SOURCES main.cpp denialofservice_tests.cpp)\nset_target_properties(test_btx PROPERTIES OUTPUT_NAME test_backport_699)\n';cmake.write_text(cmake.read_text()+overlay);(R/'test-only-cmake-overlay.txt').write_text(overlay);c.STATE['test_cmake_sha256']=c.sha(cmake)
 # Configure explicitly after final source selection; suppress only CMake's regeneration edge so Ninja can expose the actual dirty target plan.
 c.cmd(['cmake','-S',S,'-B',B,'-DCMAKE_SUPPRESS_REGENERATION=ON','-DPython3_EXECUTABLE='+c.ENV['TEST_PYTHON']],'focused-configure',180)
 _,plan=c.cmd(['ninja','-C',B,'-n','test_btx'],'actual-focused-plan')
 assert 'Re-running CMake' not in plan,'Unresolved generation-only plan'
 edges=sum(x.startswith('[') for x in plan.splitlines());c.STATE['focused_plan_edges']=edges;c.save();assert edges<=150,'Focused build unexpectedly broad'
 c.cmd(['ninja','-C',B,'-j3','test_btx'],'focused-build',480)
 exe=B/'bin/test_backport_699';c.STATE['candidate_699_sha256']=c.sha(exe)
 keep=W/'retained-baseline';keep.mkdir(exist_ok=True);shutil.copy2(exe,keep/'test_backport_699-candidate')
 code,listing=c.cmd([exe,'--list_content'],'699-contents');(R/'699-contents-exact.txt').write_text(listing)
 assert 'orphan_reconsideration_interruptible' in listing
 # The actual declared case names are pinned from the supplied source; no CTest registration or omitted source counts as execution.
 source=(S/'src/test/denialofservice_tests.cpp').read_text();import re
 names=set(re.findall(r'BOOST_(?:AUTO_TEST_CASE|FIXTURE_TEST_CASE)\(\s*(\w+)',source));assert len(names)==6,names
 assert all(name in listing for name in names),listing
 c.STATE['declared_cases']=sorted(names);c.save()
 code,text=c.cmd([exe,'--run_test=denialofservice_tests','--log_level=test_suite','--report_level=detailed'],'candidate-699-suite',180,check=False)
 c.STATE['tests'].append({'stage':'candidate','case':'699-suite','exit':code,'binary_sha256':c.sha(exe)});c.save();assert code==0 and '6 test cases' in text,'Candidate suite incomplete'
 c.apply('product',reverse=True,only=699)
 c.cmd(['ninja','-C',B,'-j3','test_btx'],'without699-build',240)
 c.STATE['without699_sha256']=c.sha(exe)
 code,text=c.cmd([exe,'--run_test=denialofservice_tests/orphan_reconsideration_interruptible','--log_level=test_suite','--report_level=detailed'],'without699-focused',180,check=False)
 c.STATE['tests'].append({'stage':'without699','case':'699-focused','exit':code,'binary_sha256':c.sha(exe)});c.save();assert code!=0 and 'connman.ProcessMessagesOnce(peer)' in text,'Missing matched699 negative signature'
 c.apply('product',only=699);c.cmd(['ninja','-C',B,'-j3','test_btx'],'restore-candidate-699',240);c.STATE['final_699_sha256']=c.sha(exe);assert c.STATE['final_699_sha256']==c.STATE['candidate_699_sha256'],'Rebuilt candidate binary differs; preserve before attributing previous suite'
 assert c.sha(B/'bin/btxd')=='cf23b285507a6eed8d12b7b026e7987acee0e7f6c1f205eb9fd0d4cafdc393fc'
 control=S/'test/functional/p2p_backport_serving_control.py';shutil.copy2(F/control.name,control);c.STATE['serving_control_sha256']=c.sha(control)
 root=W/'test-data/698-serving';root.parent.mkdir(exist_ok=True)
 code,text=c.cmd([c.ENV['TEST_PYTHON'],control,'--configfile='+str(B/'test/config.ini'),'--tmpdir='+str(root),'--nocleanup'],'698-valid-serving',90,check=False)
 c.STATE['tests'].append({'stage':'candidate','case':'698-valid-serving','exit':code,'btxd_sha256':c.sha(B/'bin/btxd')});c.save()
 for i,log in enumerate(root.rglob('*')):
  if log.is_file() and (log.suffix=='.log' or 'stderr' in str(log)):
   (R/('698-serving-runtime-'+str(i)+'.txt')).write_bytes(log.read_bytes()[-2*1024**2:])
 assert code==0,'Valid-serving control needs exact setup/product classification'
 c.STATE['complete']=True;c.STATE['acceptance']='Focused699 suite/negative and unrun698 serving control completed; prior4functionalpairs reused.';c.save()
try:main()
except Exception as e:c.STATE['error']=str(e);(R/'exception.txt').write_text(traceback.format_exc())
finally:c.save()
sys.exit(0 if c.STATE['complete'] else 1)
