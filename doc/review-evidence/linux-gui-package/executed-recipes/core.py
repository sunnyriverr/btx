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
 assert shutil.disk_usage(w).free>10*1024**3
 assert sha(checker)=='afdbcee8a34141a6368787690aeae767c59b1c85a3ce9faae336c0bb4b96cbbf'
 s['checker_sha256']=sha(checker)
 # Same final regression harness against untouched baseline source, then full maintained after-suite.
 test='test/util/package_release_archive_test.py';shutil.copy2(source/test,baseline/test)
 regressions=['BundleQtGuiTest.test_direct_private_dependency_survives_host_branch_cut','PackageReleaseArchiveTest.test_direct_guard_and_qt_keep_shared_and_private_dependencies']
 s['unit_before']={}
 for n,name in enumerate(regressions):
  r=run([sys.executable,baseline/test,name],f'unit-before-{n}',limit=90);assert r.returncode!=0
  expected='libhost_only.so.1' if n==0 else 'libbtxshared.so.1'
  assert expected in r.stdout and 'FAIL:' in r.stdout and 'ERROR:' not in r.stdout, 'Wrong baseline failure: '+r.stdout[-1500:]
  s['unit_before'][name]={'exit':r.returncode,'expected_failure':expected}
 r=run([sys.executable,source/test],'unit-after-full',limit=120);assert r.returncode==0 and 'skipped=' not in r.stdout
 s['unit_after_full_pass']=True
 # Prefix-only mutant must not let flattened ldd leak host-owned descendants back into the Qt bundle.
 mutant=runtime/'prefix-only';(mutant/'scripts/release').mkdir(parents=True);(mutant/'test/util').mkdir(parents=True)
 for name in ['package_release_archive.py','verify_release_btxd.py','support_files.txt']:
  shutil.copy2(source/'scripts/release'/name,mutant/'scripts/release'/name)
 shutil.copy2(source/test,mutant/test)
 import ast
 old=(baseline/'scripts/release/bundle_qt_gui.py').read_text();new=(source/'scripts/release/bundle_qt_gui.py').read_text()
 old_fn=next(n for n in ast.parse(old).body if isinstance(n,ast.FunctionDef) and n.name=='_ldd_map');new_fn=next(n for n in ast.parse(new).body if isinstance(n,ast.FunctionDef) and n.name=='_ldd_map')
 lines=new.splitlines(True);lines[new_fn.lineno-1:new_fn.end_lineno]=[ast.get_source_segment(old,old_fn)+'\n'];(mutant/'scripts/release/bundle_qt_gui.py').write_text(''.join(lines))
 r=run([sys.executable,mutant/test,regressions[0]],'prefix-only-negative',limit=30);assert r.returncode!=0;s['prefix_only_mutant_rejected']=True
 bad=w/'candidate-input/btx-linux-gui-candidate.tar.gz';assert sha(bad)=='03fc61615c46e6fc35fc497fc14a5ddeefcca51d3264ede72175487b694e5e3e'
 prov=json.loads((w/'candidate-input/provenance.json').read_text());assert prov['candidate_archive_sha256']==sha(bad)
 with tarfile.open(bad) as t:t.extractall(runtime/'before',filter='data')
 before=runtime/'before/btx-0.34.16';before_files=files(before);assert before_files==prov['candidate_files']
 assert gate(bad,'gate-before').returncode!=0 and len(problems('gate-before'))==2;s['gate_before_problems']=problems('gate-before')
 before_guard=run([before/'libexec/btx-guardd','--stdio'],'guard-before-direct',input='',limit=10)
 s['guard_before_direct_exit']=before_guard.returncode
 after=runtime/'after/btx-0.34.16';shutil.copytree(before,after)
 bundle=load('current_bundle',source/'scripts/release/bundle_qt_gui.py');reader=load('unchanged_checker',checker)
 private=after/'lib/qt-private';qt=after/'libexec/btx-qt.real';plugin=private/'qt6/plugins/platforms/libqxcb.so'
 loader=dict(clean,LD_LIBRARY_PATH=str(private)+':'+str(after/'lib'))
 prior_ld=os.environ.get('LD_LIBRARY_PATH');os.environ['LD_LIBRARY_PATH']=loader['LD_LIBRARY_PATH']
 try:needed=bundle._collect_private_libs([qt,plugin])
 finally:
  if prior_ld is None:os.environ.pop('LD_LIBRARY_PATH',None)
  else:os.environ['LD_LIBRARY_PATH']=prior_ld
 keep={p.resolve() for name,p in needed.items() if p.resolve().is_relative_to(private.resolve()) and not (after/'lib'/name).is_file()}|{plugin.resolve()}
 removed=[]
 for path in private.rglob('*'):
  if path.is_file() and path.resolve() not in keep:
   with path.open('rb') as f:assert f.read(4)==b'\x7fELF'
   removed.append(str(path.relative_to(after)));path.unlink()
 assert {'lib/qt-private/libglib-2.0.so.0','lib/qt-private/libdbus-1.so.3'}<=set(removed)
 s['qt_private_pruned']=sorted(removed)
 private_metadata=[]
 for path in private.rglob('*'):
  if path.is_file():
   info=reader.elf_dynamic_info(path)
   if info.needed:
    relative='$ORIGIN/../../../:$ORIGIN/../../../../' if path==plugin else '$ORIGIN:$ORIGIN/..'
    bundle._set_rpath(path,relative)
    updated=reader.elf_dynamic_info(path)
    assert info.needed==updated.needed and info.verneed==updated.verneed
    private_metadata.append(str(path.relative_to(after)))
 s['qt_private_rpath_adjusted']=private_metadata
 guard_link(after)
 original_info=reader.elf_dynamic_info(before/'libexec/btx-guardd');fixed_info=reader.elf_dynamic_info(after/'libexec/btx-guardd')
 assert original_info.needed==fixed_info.needed and original_info.verneed==fixed_info.verneed
 s['guard_rpath']=fixed_info.search
 after_files=files(after);allowed=set(removed)|set(private_metadata)|{'libexec/btx-guardd','libexec/btx-guardd.real'}
 assert all(after_files.get(n)==v for n,v in before_files.items() if n not in allowed)
 assert not(set(after_files)-set(before_files));s['all_other_files_unchanged']=True
 s['changed_files']={n:{'before':before_files.get(n),'after':after_files.get(n)} for n in sorted(set(before_files)|set(after_files)) if before_files.get(n)!=after_files.get(n)}
 corrected=outputs/'btx-linux-gui-candidate-corrected.tar.gz';archive(after,corrected)
 assert gate(corrected,'gate-after').returncode==0;s['gate_after_exit']=0
 # Corrected archive must preserve regular hard-linked guard names after extraction too.
 with tarfile.open(corrected) as t:t.extractall(runtime/'roundtrip',filter='data')
 extracted=runtime/'roundtrip/btx-0.34.16';assert files(extracted)==after_files
 assert (extracted/'libexec/btx-guardd').samefile(extracted/'libexec/btx-guardd.real')
 s['roundtrip_files']=len(after_files)
 s['loader']={}
 for label,env in [('clean',clean),('wrapper',loader)]:
  s['loader'][label]={}
  for name,path in [('qt',qt),('plugin',plugin)]:s['loader'][label][name]=resolve(path,'loader-'+label+'-'+name,env)
 for label in s['loader']:
  for name in s['loader'][label]:
   for soname in ['libglib-2.0.so.0','libdbus-1.so.3']:
    path=s['loader'][label][name]['paths'].get(soname)
    if path:assert not Path(path).resolve().is_relative_to(after.resolve())
 direct=resolve(after/'libexec/btx-guardd','guard-loader-clean',clean)
 for soname in ['libsqlite3.so.0','libstdc++.so.6','libgcc_s.so.1']:
  assert Path(direct['paths'][soname]).resolve()==(after/'lib'/soname).resolve()
 s['guard_loader']=direct
 assert run([after/'libexec/btx-guardd','--stdio'],'guard-after-direct',input='',limit=10).returncode==0
 # Negative controls use separate trees; never mutate the qualified output.
 ng=runtime/'negative-guard/btx-0.34.16';shutil.copytree(after,ng);guard_link(ng,remove=True);ngtar=runtime/'negative-guard.tar.gz';archive(ng,ngtar)
 assert gate(ngtar,'gate-negative-guard').returncode!=0 and any('libexec/btx-guardd:' in x for x in problems('gate-negative-guard'))
 nh=runtime/'negative-host/btx-0.34.16';shutil.copytree(after,nh)
 for n in removed:shutil.copy2(before/n,nh/n)
 nhtar=runtime/'negative-host.tar.gz';archive(nh,nhtar)
 assert gate(nhtar,'gate-negative-host').returncode!=0 and any('libexec/btx-atlas.real:' in x for x in problems('gate-negative-host'))
 s['archive_negatives']={'guard':problems('gate-negative-guard'),'host':problems('gate-negative-host')}
 # A source-generated package is an independent check: an empty destination cannot borrow existing root libraries.
 inputs=runtime/'inputs';(inputs/'bin').mkdir(parents=True);shutil.copytree(before/'lib',inputs/'lib')
 for path in (before/'libexec').glob('*.real'):shutil.copy2(path,inputs/'bin'/path.name[:-5])
 package=load('source_packager',source/'scripts/release/package_release_archive.py')
 retained_bundle=package._load_qt_bundle()
 retained_bundle._qt_plugins_root=lambda:inputs/'lib/qt-private/qt6/plugins'
 package._load_qt_bundle=lambda:retained_bundle
 s['fresh_stage_plugin_input_sha256']=sha(inputs/'lib/qt-private/qt6/plugins/platforms/libqxcb.so')
 s['fresh_stage_plugin_provider']='Explicit retained Qt6.2.4 build input; no host Qt6.4 plugin substitution'
 build_env=dict(clean,LD_LIBRARY_PATH=str(inputs/'lib'))
 old_env=dict(os.environ)
 try:
  os.environ.clear();os.environ.update(build_env)
  fresh,_,skipped=package.stage_release_tree(version='0.34.16',platform_id='linux-x86_64',btxd_path=inputs/'bin/btxd',btx_cli_path=inputs/'bin/btx-cli',btx_util_path=inputs/'bin/btx-util',matmul_metallib_path=None,oracle_metallib_path=None,metal_lib_dir=None,source_root=before,temp_root=runtime/'fresh-source-stage',require_gui=True,require_model_helpers=True)
 finally:os.environ.clear();os.environ.update(old_env)
 assert not skipped
 for n in ['libexec/btxd.real','bin/btxd','lib/libssl.so.3','lib/libcrypto.so.3','libexec/btx-atlas.real',*prov['dependency_graph']['protected_libraries']]:
  assert sha(fresh/n)==before_files[n]['sha256'],n
 fresh_tar=outputs/'btx-linux-gui-fresh-stage.tar.gz';package.write_tar_gz(fresh_tar,fresh)
 assert gate(fresh_tar,'gate-fresh-source-output').returncode==0
 assert run([fresh/'libexec/btx-guardd','--stdio'],'guard-fresh-stage-direct',input='',limit=10).returncode==0
 s['fresh_source_stage_gate_pass']=True
 s['fresh_loader']={}
 fresh_wrapper=dict(clean,LD_LIBRARY_PATH=str(fresh/'lib/qt-private')+':'+str(fresh/'lib'))
 for label,env in [('clean',clean),('wrapper',fresh_wrapper)]:
  s['fresh_loader'][label]={}
  for name,path in [('qt',fresh/'libexec/btx-qt.real'),('plugin',fresh/'lib/qt-private/qt6/plugins/platforms/libqxcb.so')]:
   s['fresh_loader'][label][name]=resolve(path,'fresh-loader-'+label+'-'+name,env)

 s['corrected_archive_sha256']=sha(corrected);s['fresh_source_archive_sha256']=sha(fresh_tar)
 s['node_openssl_atlas_unchanged']=True;s['prior_gui_evidence_reused']={'run':42458568275,'package_input':sha(bad),'scope':'Atlas bytes, wrapper and shared root libraries unchanged. Qt closure newly loader-qualified only; no GUI repeat.'}
 assert sha(checker)==s['checker_sha256'];s['complete']=True
 (outputs/'provenance.json').write_text(json.dumps(s,indent=2)+'\n')
except Exception as e:s['error']=repr(e)
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
