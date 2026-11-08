"""Bounded loader/archive qualification. Never launch a GUI or rebuild a BTX component."""
from pathlib import Path
import os,sys,json,hashlib,subprocess,shutil,tarfile,importlib.util,re,copy
w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'packaging-resolution-results';out.mkdir();outputs=w/'packaging-resolution-output';outputs.mkdir();runtime=w/'packaging-resolution-runtime';runtime.mkdir()
source=w;baseline=w/'baseline';checker=source/'scripts/release/verify_release_btxd.py'
s={'fixture':os.environ['GITHUB_SHA'],'source_base':'ff5f3f04ea11f044594987fc6be043ff68b136ad','gui_repeated':False,'component_rebuilds':0,'commands':[],'release_qualified':False}
clean={k:v for k,v in os.environ.items() if not k.startswith('LD_')}
(runtime/'home').mkdir(mode=0o700);clean['HOME']=str(runtime/'home')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def save():(out/'result.json').write_text(json.dumps(s,indent=2)+'\n')
def run(args,label,env=None,input=None,limit=180,cwd=None):
 s['phase']=label;save()
 p=subprocess.run(list(map(str,args)),cwd=cwd,env=env or clean,input=input,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=limit)
 (out/(label+'.log')).write_text(p.stdout);s['commands'].append({'label':label,'exit':p.returncode});save();return p

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def files(root):
 return {str(p.relative_to(root)):{'sha256':sha(p),'mode':p.stat().st_mode&0o777} for p in root.rglob('*') if p.is_file()}

def archive(root,path):
 def meta(info):info.uid=info.gid=0;info.uname=info.gname='root';return info
 with tarfile.open(path,'w:gz',compresslevel=1) as t:t.add(root,arcname=root.name,filter=meta)

def problems(label):return [line for line in (out/(label+'.log')).read_text().splitlines() if line.startswith('  - ')]
def gate(a,label):return run([sys.executable,checker,'--archive',a,'--require-model-helpers'],label)
def guard_link(root,remove=False):
 real=root/'libexec/btx-guardd.real';alias=root/'libexec/btx-guardd';alias.unlink()
 if remove:assert run(['patchelf','--remove-rpath',real],'negative-guard-edit').returncode==0
 else:load('guard_packager',source/'scripts/release/package_release_archive.py').set_linux_guard_runpath(real)
 os.link(real,alias);assert alias.is_file() and not alias.is_symlink() and alias.samefile(real)

def resolve(path,label,env):
 r=run(['ldd','-r',path],label,env=env)
 assert r.returncode==0 and not any(x in r.stdout for x in ('not found','undefined symbol:','version lookup error')),(label,r.stdout[-2000:])
 resolved=dict(re.findall(r'^\s*(\S+) => (/\S+)',r.stdout,re.M))
 return {'paths':resolved,'sha256':{name:sha(Path(p)) for name,p in resolved.items()}}
try:
 assert shutil.disk_usage(w).free>8*1024**3
 assert sha(checker)=='afdbcee8a34141a6368787690aeae767c59b1c85a3ce9faae336c0bb4b96cbbf'
 bad=w/'candidate-input/btx-linux-gui-candidate.tar.gz'
 assert sha(bad)=='03fc61615c46e6fc35fc497fc14a5ddeefcca51d3264ede72175487b694e5e3e'
 prov=json.loads((w/'candidate-input/provenance.json').read_text())
 with tarfile.open(bad) as t:t.extractall(runtime/'before',filter='data')
 before=runtime/'before/btx-0.34.16';before_files=files(before);assert before_files==prov['candidate_files']
 previous=json.loads((w/'prior-records/packaging-resolution-results/result.json').read_text())
 assert previous['fixture']=='3ea43156261a966f6c8e52fbd76daebee3192285'
 assert previous['unit_after_full_pass'] and previous['gate_after_exit']==0 and previous['all_other_files_unchanged']
 for label in ['clean','wrapper']:
  assert set(previous['loader'][label])=={'qt','plugin'}
 s['reused_completed_run']=42460862377
 s['reused_source_code']='400f863ea082d8b6b9b0c6fb99e2e09224001266'
 s['prior_records_sha256']=sha(w/'prior-records/packaging-resolution-results/result.json')
 # Verify the already-qualified corrected archive's uploaded bytes against its recorded full file manifest.
 corrected=w/'prior-candidates/btx-linux-gui-candidate-corrected.tar.gz'
 with tarfile.open(corrected) as t:t.extractall(runtime/'corrected',filter='data')
 expected=dict(before_files)
 for name,change in previous['changed_files'].items():
  if change['after'] is None:expected.pop(name)
  else:expected[name]=change['after']
 after=runtime/'corrected/btx-0.34.16';assert files(after)==expected
 s['corrected_archive_sha256']=sha(corrected);s['corrected_uploaded_file_manifest_matches']=True
 # A source-generated package is an independent check: an empty destination cannot borrow existing root libraries.
 inputs=runtime/'inputs';(inputs/'bin').mkdir(parents=True);shutil.copytree(before/'lib',inputs/'lib')
 for path in (before/'libexec').glob('*.real'):shutil.copy2(path,inputs/'bin'/path.name[:-5])
 package=load('source_packager',source/'scripts/release/package_release_archive.py')
 retained_bundle=package._load_qt_bundle()
 retained_bundle._qt_plugins_root=lambda:inputs/'lib/qt-private/qt6/plugins'
 package._load_qt_bundle=lambda:retained_bundle
 s['fresh_stage_plugin_input_sha256']=sha(inputs/'lib/qt-private/qt6/plugins/platforms/libqxcb.so')
 s['fresh_stage_plugin_provider']='Explicit retained Qt6.2.4 build input; no host Qt6.4 plugin substitution'
 build_env=dict(clean,LD_LIBRARY_PATH=str(inputs/'lib')+':'+str(inputs/'lib/qt-private'))
 old_env=dict(os.environ)
 try:
  os.environ.clear();os.environ.update(build_env)
  fresh,_,skipped=package.stage_release_tree(version='0.34.16',platform_id='linux-x86_64',btxd_path=inputs/'bin/btxd',btx_cli_path=inputs/'bin/btx-cli',btx_util_path=inputs/'bin/btx-util',matmul_metallib_path=None,oracle_metallib_path=None,metal_lib_dir=None,source_root=before,temp_root=runtime/'fresh-source-stage',require_gui=True,require_model_helpers=True)
 finally:os.environ.clear();os.environ.update(old_env)
 assert not skipped
 for n in ['libexec/btxd.real','bin/btxd','lib/libssl.so.3','lib/libcrypto.so.3','libexec/btx-atlas.real','bin/btx-atlas']:
  assert sha(fresh/n)==before_files[n]['sha256'],n
 s['fresh_stage_retained_root_libraries']=[]
 s['fresh_stage_omitted_input_root_libraries']=[]
 for n in prov['dependency_graph']['protected_libraries']:
  if (fresh/n).is_file():
   assert sha(fresh/n)==before_files[n]['sha256'],n
   s['fresh_stage_retained_root_libraries'].append(n)
  else:s['fresh_stage_omitted_input_root_libraries'].append(n)
 s['fresh_stage_library_scope']='Fresh producer stages OpenSSL and the shared Qt candidate subgraph, not every library carried in the saved archive. Omitted inputs are explicit; unchanged default gate and clean loader checks remain mandatory.'

 fresh_tar=outputs/'btx-linux-gui-fresh-stage.tar.gz';package.write_tar_gz(fresh_tar,fresh)
 assert gate(fresh_tar,'gate-fresh-source-output').returncode==0
 assert run([fresh/'libexec/btx-guardd','--stdio'],'guard-fresh-stage-direct',input='',limit=10).returncode==0
 s['fresh_guard_loader']=resolve(fresh/'libexec/btx-guardd','fresh-guard-loader-clean',clean)
 s['fresh_source_stage_gate_pass']=True
 s['fresh_loader']={}
 fresh_wrapper=dict(clean,LD_LIBRARY_PATH=str(fresh/'lib/qt-private')+':'+str(fresh/'lib'))
 for label,env in [('clean',clean),('wrapper',fresh_wrapper)]:
  s['fresh_loader'][label]={}
  for name,path in [('qt',fresh/'libexec/btx-qt.real'),('plugin',fresh/'lib/qt-private/qt6/plugins/platforms/libqxcb.so')]:
   s['fresh_loader'][label][name]=resolve(path,'fresh-loader-'+label+'-'+name,env)

 s['fresh_source_archive_sha256']=sha(fresh_tar)
 s['node_openssl_atlas_unchanged']=True
 s['prior_gui_evidence_reused']={'run':42458568275,'scope':'Unchanged Atlas/wrapper/root inputs; no GUI execution in this run'}
 s['complete']=True
 (outputs/'provenance.json').write_text(json.dumps(s,indent=2)+'\n')
except Exception as e:
 import traceback
 s['error']=repr(e);s['traceback']=traceback.format_exc()
 (out/'exception.log').write_text(s['traceback'])
finally:
 remaining=[]
 for process in Path('/proc').iterdir():
  if process.name.isdigit():
   try:
    if Path(os.readlink(process/'exe')).is_relative_to(runtime):remaining.append(int(process.name))
   except OSError:pass
 s['remaining_package_processes']=remaining
 if s.get('complete') and not remaining:shutil.rmtree(runtime)
 s['runtime_removed']=not runtime.exists();save()
raise SystemExit(0 if s.get('complete') and not s.get('error') else 1)
