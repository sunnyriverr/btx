from pathlib import Path
import os,json,tarfile,shutil,time,sys,traceback
import run as c
c.EXECUTION_LIMIT=1800
W,S,B,R,F=c.W,c.S,c.B,c.R,c.F
c.STATE.update(base='f40eb37a6fb8b665340fe92a2f248ff3f23ec7f6',scope='M3 current package executables and M4 two affected wallet functional checks')
def main():
 assert shutil.disk_usage(W).free>15*1024**3
 _,head=c.cmd(['git','-C',S,'rev-parse','HEAD'],'source');assert head.strip()==c.STATE['base']
 c.cmd(['xcodebuild','-version'],'xcode');_,clang=c.cmd(['xcrun','clang++','--version'],'clang');assert 'Apple clang version 17.0.0' in clang
 _,sdk=c.cmd(['xcrun','--sdk','macosx','--show-sdk-version'],'sdk');assert sdk.strip()=='15.5'
 payload=W/'producer-restore';receipt=json.loads((payload/'receipt.json').read_text());assert receipt['sha256']=='51d37cb5e5a99e8c6b69f1f7877b1c652215c9fbd0978ee3a0fe29b7ac45e685';assert c.sha(payload/'checkpoint.tar.gz')==receipt['sha256']
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
 assert c.STATE['actual_edges']<=160,'Actual build cost exceeds admitted120edge margin'
 c.cmd(['ninja','-C',B,'-j3',*targets],'current-package-binaries-build',900)
 c.STATE['btx_compiled']=True;c.STATE['binary_manifest']={name:c.sha(B/'bin'/name) for name in targets};c.save()
 c.cmd(['git','-C',S,'status','--porcelain'],'built-source-status',30)
 for file in ['wallet_recipient_amount_range.py','wallet_shielded_birth_time_restart.py']:
  root=W/'test-data'/file.removesuffix('.py');root.parent.mkdir(exist_ok=True)
  code,text=c.cmd([c.ENV['TEST_PYTHON'],S/'test/functional'/file,'--descriptors','--configfile='+str(B/'test/config.ini'),'--tmpdir='+str(root),'--nocleanup'],file.removesuffix('.py'),240,check=False)
  c.STATE['tests'].append({'case':file,'exit':code,'btxd_sha256':c.sha(B/'bin/btxd')});c.save()
  for i,log in enumerate(root.rglob('*')):
   if log.is_file() and (log.suffix=='.log' or 'stderr' in str(log)):(R/(file+'-runtime-'+str(i)+'.txt')).write_bytes(log.read_bytes()[-2*1024**2:])
 out=W/'retained';out.mkdir(exist_ok=True);metal={}
 for f in B.rglob('*.metallib'):
  digest=c.sha(f)
  assert f.name not in metal or metal[f.name]['sha256']==digest,'Different Metal libraries share a name'
  metal[f.name]={'path':str(f),'sha256':digest}
 assert len(metal)>=7,'Missing compiled Metal library inventory'
 with tarfile.open(out/'current-executables.tar.gz','w:gz') as tar:
  for name in targets:tar.add(B/'bin'/name,arcname='bin/'+name,recursive=False)
  for name,row in metal.items():tar.add(row['path'],arcname='metal/'+name,recursive=False)
 manifest={'source':c.STATE['base'],'binaries':c.STATE['binary_manifest'],'metal':metal,'archive_sha256':c.sha(out/'current-executables.tar.gz'),'profile':'CMakeCache retained in records; nativeMac15ARM64; noGUI executables included'}
 (out/'current-executables-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');c.STATE['export']=manifest
 c.STATE['complete']=all(x['exit']==0 for x in c.STATE['tests']);c.save()

try:main()
except Exception as e:c.STATE['error']=str(e);(R/'exception.txt').write_text(traceback.format_exc())
finally:c.save()
sys.exit(0 if c.STATE['complete'] else 1)
