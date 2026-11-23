from pathlib import Path
import os,sys,json,subprocess,tarfile,shutil,time,selectors,signal,hashlib
from checkpoint import sha,restore_timestamps,verify_restored,create
HEAD='932a0238c70705b28ea344a7929cee09ada314c8';OLD='7d65025bb3bff27e4f6c2fdc95f33e4b859a2df5';ARCHIVE='2fae3dc0b4b51c4c5acd08a30ec5070d4aaa2705ab7a237854158edb58db5170'
w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'records';out.mkdir(exist_ok=True);r={'source':HEAD,'checkpoint_source':OLD,'complete':False,'commands':[]};restored=False

def save():(out/'build-result.json').write_text(json.dumps(r,indent=2)+'\n')
def run(cmd,label,limit=120,cwd=None,expected=0):
 p=subprocess.Popen([str(x) for x in cmd],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,cwd=cwd,start_new_session=True);start=time.monotonic();data=[];sel=selectors.DefaultSelector();sel.register(p.stdout,selectors.EVENT_READ)
 with (out/(label+'.log')).open('wb') as f:
  while p.poll() is None or sel.get_map():
   for key,_ in sel.select(.5):
    chunk=os.read(key.fileobj.fileno(),65536)
    if not chunk:sel.unregister(key.fileobj);continue
    f.write(chunk);f.flush();data.append(chunk);sys.stdout.buffer.write(chunk);sys.stdout.flush()
   if (time.monotonic()-start>limit or shutil.disk_usage(w).free<2*1024**3) and p.poll() is None:
    os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(10)
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
  p.wait()
 r['commands'].append({'step':label,'exit':p.returncode,'seconds':time.monotonic()-start});save()
 if p.returncode!=expected:raise RuntimeError(label+' exit '+str(p.returncode))
 return b''.join(data).decode(errors='replace')
try:
 m=json.loads((w/'saved-checkpoint/manifest.json').read_text());arc=w/'saved-checkpoint/build-state.tar.gz'
 assert sha(arc)==ARCHIVE==m['archive_sha256'] and m['identity']['source']==OLD
 assert m['workspace']==str(w) and shutil.disk_usage(w).free>10*1024**3
 with tarfile.open(arc) as t:t.extractall(w,filter='data')
 restore_timestamps(w,m);verify_restored(w,m);restored=True;r['checkpoint_verified']=True;save()
 source=w/'product';accepted=w/'accepted-source';build=w/'gui-pilot-runtime/qtbuild'
 assert run(['git','rev-parse','HEAD'],'accepted-head',cwd=accepted).strip()==HEAD
 names=run(['git','ls-files'],'accepted-files',cwd=accepted).splitlines();current=set(names)
 # Preserve generated/untracked cache files; remove only audited deleted tracked files.
 for entry in json.loads((w/'source-delta.json').read_text()):
  if entry['status']=='removed':
   b=source/entry['filename']
   if b.exists() or b.is_symlink():b.unlink()
 changed=[]
 for name in names:
  a=accepted/name;b=source/name
  same=(a.is_symlink() and b.is_symlink() and os.readlink(a)==os.readlink(b)) or (not a.is_symlink() and b.is_file() and not b.is_symlink() and sha(a)==sha(b))
  if not same:
   b.parent.mkdir(parents=True,exist_ok=True)
   if b.is_symlink():b.unlink()
   if a.is_symlink():b.symlink_to(os.readlink(a))
   else:shutil.copy2(a,b)
   changed.append(name)
  if not a.is_symlink():os.chmod(b,a.stat().st_mode & 0o777)
  assert (b.is_symlink() and a.is_symlink() and os.readlink(a)==os.readlink(b)) or (not a.is_symlink() and sha(a)==sha(b) and (a.stat().st_mode&0o777)==(b.stat().st_mode&0o777)),name
 assert set(changed) == {row['filename'] for row in json.loads((w/'source-delta.json').read_text())}
 r['changed_source_files']=changed;r['source_verified']=True
 r['patch_sha256']=sha(w/'candidate.patch')
 if (source/'.git').exists():shutil.rmtree(source/'.git')
 shutil.copytree(accepted/'.git',source/'.git')
 assert 'OpenSSL 3.5.9' in run([w/'gui-pilot-runtime/openssl/bin/openssl','version'],'openssl')
 assert run(['g++','-dumpfullversion'],'gcc').strip()=='11.4.0'
 assert '3.31.6' in run(['cmake','--version'],'cmake')

 run(['git','apply','--check',w/'candidate.patch'],'patch-check',cwd=source)
 run(['git','apply',w/'candidate.patch'],'patch-apply',cwd=source)
 run(['cmake','-S',source,'-B',build],'configure',180)
 globs=run(['cmake','-P',build/'CMakeFiles/VerifyGlobs.cmake'],'verify-globs',120,cwd=build)
 assert 'GLOB mismatch!' not in globs
 targets=['btx-hcpd','btx-capabilityd','btx-capability','btx-modeld']
 plan=run(['ninja','-C',build,'-n',*targets],'dry-run',120)
 steps=[line for line in plan.splitlines() if line.startswith('[')]
 assert 0<len(steps)<=150,len(steps)
 r['planned_steps']=len(steps);save()
 run(['cmake','--build',build,'--parallel','2','--target',*targets],'build',1080)
 r['binary_sha256']={name:sha(build/'bin'/name) for name in targets};save()
 run([sys.executable,w/'diagnostics.py','capture',build/'bin',out/'candidate.json'],'candidate-diagnostics',80)
 run([sys.executable,w/'diagnostics.py','compare',out/'stock.json',out/'candidate.json'],'comparison',15)
 r['complete']=True
except Exception as e:
 r['error']=repr(e);print('BUILD ERROR',repr(e),flush=True)
finally:
 save()
raise SystemExit(0 if r['complete'] else 1)
