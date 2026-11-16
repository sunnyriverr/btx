from pathlib import Path
import os,json,subprocess,tarfile,shutil,time,hashlib,sys
from checkpoint import sha,restore_timestamps,verify_restored,create
w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'records';out.mkdir(exist_ok=True);build=w/'gui-pilot-runtime/qtbuild';source=w/'product';accepted=w/'accepted-source'
r={'source':'1e2f8b5f12295002334d3390c12cac0bb4ae2aff','status':'INCOMPLETE','commands':[],'scope':'Focused Linux hydration helper and selected maintained test bodies; no full suite'}
def save():(out/'build-result.json').write_text(json.dumps(r,indent=2)+'\n')
def run(cmd,label,cap=120,cwd=None,expected=0,env=None):
 start=time.monotonic()
 with (out/(label+'.log')).open('w') as log:
  p=subprocess.run([str(x) for x in cmd],stdout=log,stderr=subprocess.STDOUT,cwd=cwd,timeout=cap,env=env)
 text=(out/(label+'.log')).read_text(errors='replace');print(text[-5000:],flush=True)
 r['commands'].append({'label':label,'exit':p.returncode,'seconds':round(time.monotonic()-start,3)});save()
 assert p.returncode==expected,(label,p.returncode)
 return text
try:
 m=json.loads((w/'saved-checkpoint/manifest.json').read_text());arc=w/'saved-checkpoint/build-state.tar.gz'
 assert m['archive_sha256']==sha(arc)=='e2b4e38fe2820002622e7e6c94259d3fd617df23299de2f2bf3fb9109a2c3628'
 assert m['workspace']==str(w) and shutil.disk_usage(w).free>10*1024**3
 with tarfile.open(arc) as t:t.extractall(w,filter='data')
 restore_timestamps(w,m);verify_restored(w,m);r['checkpoint_verified']=True;save()
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=accepted,text=True).strip()==r['source']
 changed=[]
 for n in subprocess.check_output(['git','ls-files'],cwd=accepted,text=True).splitlines():
  a=accepted/n;b=source/n
  same=(a.is_symlink() and b.is_symlink() and os.readlink(a)==os.readlink(b)) or (not a.is_symlink() and b.is_file() and not b.is_symlink() and sha(a)==sha(b))
  if not same:
   b.parent.mkdir(parents=True,exist_ok=True)
   if b.is_symlink():b.unlink()
   if a.is_symlink():b.symlink_to(os.readlink(a))
   else:shutil.copy2(a,b)
   changed.append(n)
 r['baseline_restored_source_files']=changed
 if (source/'.git').exists():shutil.rmtree(source/'.git')
 shutil.copytree(accepted/'.git',source/'.git')
 # Qualification-only executable: production archives and exact maintained case bodies.
 cm=source/'src/modelnet/CMakeLists.txt';cm.write_text(cm.read_text()+f'\nadd_executable(review737 "{w}/component.cpp")\ntarget_link_libraries(review737 core_interface)\ntarget_link_btx_linux_archive_group(review737 bitcoin_modelnet ${{BTX_BASE_ARCHIVES}})\n')
 generated=build/'src/matmul-rc-production-golden-manifest-data.h';old=(sha(generated),generated.stat().st_mtime_ns) if generated.exists() else None
 run(['cmake','-S',source,'-B',build],'configure',180)
 if old and sha(generated)==old[0]:os.utime(generated,ns=(generated.stat().st_atime_ns,old[1]))
 cases=['job_cleanup_failure_preserves_valid_eof_checkpoint','missing_eof_quarantine_does_not_advance_resume_cursor','short_final_checkpoint_survives_publication_quota_failure','only_complete_file_integrity_mismatches_mark_rejection','finished_hydration_releases_its_quarantine_copy']
 for phase in ['baseline','candidate']:
  if phase=='candidate':
   assert sha(source/'src/modelnet/file_stream.cpp')==sha(w/'base-file_stream.cpp')
   shutil.copyfile(w/'file_stream.cpp',source/'src/modelnet/file_stream.cpp')
  run(['cmake','-P',build/'CMakeFiles/VerifyGlobs.cmake'],phase+'-verify-globs')
  graph=out/(phase+'.ninja');shutil.copyfile(build/'build.ninja',graph)
  text=run(['ninja','-C',build,'-f',graph,'-n','btx-modeld','review737'],phase+'-plan')
  actions=[l for l in text.splitlines() if l.startswith('[')];assert len(actions)<=80 and 'Re-running CMake' not in text,actions
  r[phase+'_plan']=actions;save()
  run(['ninja','-C',build,'-f',graph,'-j2','btx-modeld','review737'],phase+'-build',900)
  dest=w/'built'/phase;dest.mkdir(parents=True)
  for n in ['btx-modeld','review737']:shutil.copy2(build/'bin'/n,dest/n)
  r[phase+'_helper_sha256']=sha(dest/'btx-modeld');r[phase+'_component_sha256']=sha(dest/'review737');save()
  for index,name in enumerate(cases):
   run([dest/'review737',name,w/f'component-scratch-{phase}-{index}'],phase+'-'+name,30,expected=1 if phase=='baseline' and index<2 else 0)
  env={**os.environ,'BTX737_HELPER':str(dest/'btx-modeld'),'BTX737_HELPER_SHA':sha(dest/'btx-modeld'),'BTX737_CREATOR':str(w/'binary/baseline/btx-modeld'),'BTX737_OUTPUT':str(out/('native-'+phase))}
  if phase=='baseline':
   nr=json.loads((out/'native-baseline-host/result.json').read_text());assert nr['helper_sha256']=='cb783882585291c6ab7d5f0796129336d36dc3963be3db2310bbd25fe6737eae'
   r['baseline_native_reused']='same-final-fixture pre-build original-helper host result';save()
   r[phase+'_native']=nr['status'];r[phase+'_native_failures']=nr.get('failures');save()
   assert nr['owned_helpers_exited'] and nr['scratch_removed']
   assert nr['status']=='FAIL' and set(nr['failures'])=={'interrupted_restart_not_local','legacy_restart_not_local'}
  else:
   r['candidate_native']='AWAIT_SAME_HOST_RUNTIME'
 r['status']='BUILDS_AND_COMPONENTS_PASS_HOST_RUNTIME_PENDING'
except Exception as e:r['status']='INCOMPLETE';r['error']=repr(e);print(repr(e),flush=True)
finally:
 try:
  if (source/'src/modelnet/file_stream.cpp').exists():r['saved_checkpoint_sha256']=create(w,w/'resume-checkpoint',{'source':r['source'],'status':r['status']})['archive_sha256']
 except Exception as e:r['checkpoint_error']=repr(e)
 for p in w.glob('component-scratch-*'):shutil.rmtree(p)
 r['component_scratch_removed']=not list(w.glob('component-scratch-*'));save()
raise SystemExit(0 if r['status']=='BUILDS_AND_COMPONENTS_PASS_HOST_RUNTIME_PENDING' else 1)
