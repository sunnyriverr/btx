from pathlib import Path
import os,json,tarfile,shutil,time,sys,traceback
import run as c
c.EXECUTION_LIMIT=1200
W,S,B,R,F=c.W,c.S,c.B,c.R,c.F
c.STATE.update(base='f40eb37a6fb8b665340fe92a2f248ff3f23ec7f6',scope='M2 configure and actual build plan only; no BTX compilation/runtime')
def main():
 assert shutil.disk_usage(W).free>15*1024**3
 _,head=c.cmd(['git','-C',S,'rev-parse','HEAD'],'source');assert head.strip()==c.STATE['base']
 c.cmd(['xcodebuild','-version'],'xcode');_,clang=c.cmd(['xcrun','clang++','--version'],'clang');assert 'Apple clang version 17.0.0' in clang
 _,sdk=c.cmd(['xcrun','--sdk','macosx','--show-sdk-version'],'sdk');assert sdk.strip()=='15.5'
 payload=W/'producer-restore';receipt=json.loads((payload/'receipt.json').read_text());assert receipt['sha256']=='d0b55b83144de2423e6ebd9573dae33b97601069c3b63df323ad076808a5a5a3';assert c.sha(payload/'checkpoint.tar.gz')==receipt['sha256']
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

 c.cmd(['cmake','-S',S,'-B',B,'-DCMAKE_SUPPRESS_REGENERATION=ON','-DPython3_EXECUTABLE='+c.ENV['TEST_PYTHON']],'current-configure',180)
 targets=['btxd','btx-cli','btx-util','btx-modeld','btx-hcpd','btx-hosted','btx-open','btx-capability','btx-capabilityd','btx-modelcheck','btx-matmul-backend-info','btx-security','btx-guardd','btx-tx','btx-wallet','btx-native-qualify']
 _,plan=c.cmd(['ninja','-C',B,'-n',*targets],'current-actual-package-plan',120)
 assert 'Re-running CMake' not in plan
 c.STATE['targets']=targets;c.STATE['actual_edges']=sum(x.startswith('[') for x in plan.splitlines())
 c.cmd(['ninja','-C',B,'-t','commands',*targets],'current-generated-commands',120)
 shutil.copy2(B/'CMakeCache.txt',R/'CMakeCache.txt')
 c.STATE['complete']=True;c.STATE['btx_compiled']=False;c.save()
try:main()
except Exception as e:c.STATE['error']=str(e);(R/'exception.txt').write_text(traceback.format_exc())
finally:c.save()
sys.exit(0 if c.STATE['complete'] else 1)
