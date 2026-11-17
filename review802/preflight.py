from pathlib import Path
import hashlib,json,os,shutil,subprocess,tarfile,time,traceback
from checkpoint import sha,restore_timestamps,verify_restored
w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'records';out.mkdir(exist_ok=True);source=w/'product';accepted=w/'accepted-source';build=w/'gui-pilot-runtime/qtbuild'
r={'scope':'source/configuration/target-graph preflight only; no product test/build','status':'INCOMPLETE','source':'895388354cd8b07a947ee245dc555eb02f0e96f6','commands':[],'object_reuse_allowed':False}
def save():(out/'preflight.json').write_text(json.dumps(r,indent=2)+'\n')
def run(cmd,label,cap=150,cwd=None):
 start=time.monotonic()
 with (out/(label+'.log')).open('w') as f:p=subprocess.run([str(x) for x in cmd],cwd=cwd,stdout=f,stderr=subprocess.STDOUT,timeout=cap)
 r['commands'].append({'label':label,'exit':p.returncode,'seconds':round(time.monotonic()-start,3)});save()
 text=(out/(label+'.log')).read_text(errors='replace');print(label,p.returncode,text[-4000:],flush=True)
 assert p.returncode==0,(label,p.returncode)
 return text
try:
 m=json.loads((w/'saved-checkpoint/manifest.json').read_text());arc=w/'saved-checkpoint/build-state.tar.gz'
 r['checkpoint_identity']=m['identity'];r['checkpoint_workspace']=m['workspace'];r['checkpoint_archive_sha256']=m['archive_sha256'];save()
 assert m['workspace']==str(w) and sha(arc)==m['archive_sha256'] and shutil.disk_usage(w).free>10*1024**3
 with tarfile.open(arc) as t:t.extractall(w,filter='data')
 restore_timestamps(w,m);verify_restored(w,m);r['checkpoint_all_bytes_verified']=True;save()
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=accepted,text=True).strip()==r['source']
 # The checkpoint contains source/config/build outputs and internal OpenSSL/Qt,
 # not a historical fingerprint of every system header/library/tool binary.
 # No object reuse is claimed: invalidate all old project native outputs.
 invalid=[]
 for p in list(build.rglob('*')):
  if p.is_file() and (p.suffix in ('.o','.a','.so') or p.parent==build/'bin'):
   invalid.append({'path':str(p.relative_to(w)),'bytes':p.stat().st_size});p.unlink()
 r['invalidated_native_outputs']=invalid;r['external_input_limit']='System headers/library/compiler hashes were not captured in the old manifest; cached project object reuse is disallowed, despite known tool/package versions.';save()
 changed=[]
 for name in subprocess.check_output(['git','ls-files'],cwd=accepted,text=True).splitlines():
  a=accepted/name;b=source/name
  same=(a.is_symlink() and b.is_symlink() and os.readlink(a)==os.readlink(b)) or (not a.is_symlink() and b.is_file() and not b.is_symlink() and sha(a)==sha(b))
  if not same:
   b.parent.mkdir(parents=True,exist_ok=True)
   if b.is_symlink():b.unlink()
   if a.is_symlink():b.symlink_to(os.readlink(a))
   else:shutil.copy2(a,b)
   changed.append(name)
 if (source/'.git').exists():shutil.rmtree(source/'.git')
 shutil.copytree(accepted/'.git',source/'.git');r['changed_source_files']=changed;save()
 # Target-graph placeholder only. No production contract is inferred from it.
 (w/'graph-only.cpp').write_text('int main() { return 0; }\n')
 cm=source/'src/modelnet/CMakeLists.txt';cm.write_text(cm.read_text()+f'\nadd_executable(review802 "{w}/graph-only.cpp")\ntarget_link_libraries(review802 core_interface)\ntarget_link_btx_linux_archive_group(review802 bitcoin_modelnet ${{BTX_BASE_ARCHIVES}})\n')
 run(['cmake','-S',source,'-B',build,'-DBUILD_TESTS=OFF'],'configure',180)
 cache=(build/'CMakeCache.txt').read_text();(out/'CMakeCache.txt').write_text(cache)
 assert 'WITH_MODELNET:BOOL=ON' in cache,'ModelNet not enabled'
 run(['cmake','-P',build/'CMakeFiles/VerifyGlobs.cmake'],'verify-globs',60)
 graph=out/'preflight.ninja';shutil.copyfile(build/'build.ninja',graph)
 for targets,label in [(['btx-modeld','review802'],'helper-controller-plan'),(['btx-modeld'],'helper-only-plan')]:
  text=run(['ninja','-C',build,'-f',graph,'-n',*targets],label,90)
  actions=[line for line in text.splitlines() if line.startswith('[')];r[label]={'actions':len(actions),'compiles':sum('Building ' in x for x in actions),'links':sum('Linking ' in x for x in actions)};save()
 r['status']='CONFIGURED_FRESH_NATIVE_BUILD_PLAN_ONLY';r['next']='Run fresh-object bounded native build if warranted; old binaries/objects cannot qualify802 unchanged.'
except Exception as e:r['error']=repr(e);r['traceback']=traceback.format_exc();print(r['traceback'],flush=True)
finally:save()
raise SystemExit(0 if r['status']=='CONFIGURED_FRESH_NATIVE_BUILD_PLAN_ONLY' else 1)
