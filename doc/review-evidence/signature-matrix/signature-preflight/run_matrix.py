import os,sys,json,subprocess,hashlib,shutil,importlib.util,time,signal
from pathlib import Path
from datetime import datetime,timezone
r=Path(__file__).resolve().parent;prefix=Path('/private/tmp/btx-s3-gpg-runtime');source=r.parent/'source';reserve=int(1.25*2**30)
if shutil.disk_usage('.').free<reserve+8*2**20:raise SystemExit('RESOURCE BLOCK: reserve plus 8MiB scratch not available; no keys created')
assert (prefix/'bin/gpg').is_file();homes=[prefix/x for x in ['a','b','v','empty']];assert not any(x.exists() for x in homes)
env={**os.environ,'DYLD_LIBRARY_PATH':str(prefix/'lib'),'LC_ALL':'C','PYTHONDONTWRITEBYTECODE':'1','BTX_TEST_SECRET':'fixture-only'}
for k in ['GPG_AGENT_INFO','SSH_AUTH_SOCK','GPG_TTY']:env.pop(k,None)
for home in homes:home.mkdir(mode=0o700)
raw=[];results=[];fingerprints={};work=prefix/'fixtures';work.mkdir();began=time.monotonic();agents=[]
def gp(home,args,secret=False):
 cmd=[str(prefix/'bin/gpg'),'--no-options','--homedir',str(home),'--batch','--no-auto-key-retrieve','--auto-key-locate','clear','--agent-program',str(prefix/'bin/gpg-agent')]+args
 run=subprocess.run(cmd,env={**env,'GNUPGHOME':str(home)},input='fixture-only\n' if secret else None,capture_output=True,text=True,timeout=45)
 raw.append({'command':cmd,'exit':run.returncode,'stdout':run.stdout,'stderr':run.stderr});return run
sys.path.insert(0,str(source/'scripts/release'));import sign_release_bundle as sign;import publish_github_release as pub;import collect_release_assets as collect
# Modules remain unmodified; all signing and verification subprocesses are real GPG.
def wrapper(home,name):
 p=prefix/name;p.write_text('#!/usr/bin/python3\nimport os,sys\nos.environ["GNUPGHOME"]='+repr(str(home))+'\nos.environ["DYLD_LIBRARY_PATH"]='+repr(str(prefix/'lib'))+'\nos.execv('+repr(str(prefix/'bin/gpg'))+', ["gpg", "--no-options", "--homedir", '+repr(str(home))+', "--batch", "--no-auto-key-retrieve", "--auto-key-locate", "clear"]+sys.argv[1:])\n');p.chmod(0o700);return str(p)

def fixture(name):
 p=work/name;p.mkdir();(p/'asset.bin').write_bytes(b'inert release fixture\n');(p/'btx-release-manifest.json').write_text(json.dumps({'format_version':1,'checksum_file':'SHA256SUMS','signature_file':None,'release_tag':'v0.0.0-test'})+'\n');collect.write_checksum_file(p,'SHA256SUMS');pub.ensure_bundle(p);return p
def signing(p,selector,expected,wrap):
 cmd=[sys.executable,'-B',str(source/'scripts/release/sign_release_bundle.py'),'--bundle-dir',str(p),'--sign-with',selector,'--expected-signing-fingerprint',expected,'--gpg',wrap,'--gpg-passphrase-env','BTX_TEST_SECRET'];run=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=45);raw.append({'command':cmd,'exit':run.returncode,'stdout':run.stdout,'stderr':run.stderr});return run
try:
 for home in homes:
  agent=subprocess.Popen([str(prefix/'bin/gpg-agent'),'--homedir',str(home),'--daemon','--no-detach','--allow-loopback-pinentry','--log-file',str(prefix/(home.name+'-agent.log'))],env={**env,'GNUPGHOME':str(home)},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);agents.append(agent)
  deadline=time.monotonic()+5
  while not (home/'S.gpg-agent').exists():
   assert time.monotonic()<deadline and agent.poll() is None,'Owned agent did not start';time.sleep(.05)
 for home,label,usage in [(homes[0],'A','cert'),(homes[1],'B','sign')]:
  run=gp(home,['--pinentry-mode','loopback','--passphrase-fd','0','--quick-generate-key','BTX disposable '+label+' <fixture-'+label.lower()+'@example.invalid>','rsa2048',usage,'1d'],True);assert run.returncode==0,run.stderr
  listing=gp(home,['--with-colons','--list-keys']);fpr=next(x.split(':')[9] for x in listing.stdout.splitlines() if x.startswith('fpr:'));fingerprints[label]=fpr;assert len(fpr)==40
 A=fingerprints['A'];B=fingerprints['B'];run=gp(homes[0],['--pinentry-mode','loopback','--passphrase-fd','0','--quick-add-key',A,'rsa2048','sign','1d'],True);assert run.returncode==0,run.stderr
 listing=gp(homes[0],['--with-colons','--list-keys']);sub=[x.split(':')[9] for x in listing.stdout.splitlines() if x.startswith('fpr:')][1];fingerprints['A_signing_subkey']=sub
 for home in homes[:2]:
  export=gp(home,['--armor','--export']);imp=subprocess.run([str(prefix/'bin/gpg'),'--no-options','--homedir',str(homes[2]),'--batch','--import'],env={**env,'GNUPGHOME':str(homes[2])},input=export.stdout,capture_output=True,text=True,timeout=20);raw.append({'stage':'public-key-import','exit':imp.returncode,'stdout':imp.stdout,'stderr':imp.stderr});assert imp.returncode==0,imp.stderr
 wa=wrapper(homes[0],'gpg-a');wb=wrapper(homes[1],'gpg-b');wv=wrapper(homes[2],'gpg-v');we=wrapper(homes[3],'gpg-empty');results.append({'id':'G0','result':'PASS','scope':'two disposable principals, isolated verifier+empty homes'})
 p=fixture('validA');run=signing(p,sub+'!',A,wa);assert run.returncode==0,run.stderr;sig=pub.verify_bundle_signature(p,pub.load_release_manifest(p),wv,required=True,expected_fingerprint=A);assert A in sig and sub in sig;pub.ensure_bundle(p);results.append({'id':'R1','result':'PASS','fingerprints':sorted(sig)})
 q=work/'changed-sums';shutil.copytree(p,q);(q/'SHA256SUMS').write_bytes((q/'SHA256SUMS').read_bytes()+b'\n')
 try:pub.verify_bundle_signature(q,pub.load_release_manifest(q),wv,required=True,expected_fingerprint=A);raise AssertionError('altered checksums accepted')
 except RuntimeError as e:assert 'signature verification failed' in str(e);results.append({'id':'R2','result':'PASS','rejection':str(e)})
 q=work/'changed-asset';shutil.copytree(p,q);(q/'asset.bin').write_bytes(b'changed');pub.verify_bundle_signature(q,pub.load_release_manifest(q),wv,required=True,expected_fingerprint=A)
 try:pub.ensure_bundle(q);raise AssertionError('changed content accepted')
 except RuntimeError as e:assert 'SHA256SUMS mismatch' in str(e);results.append({'id':'R3','result':'PASS','valid_signature':True,'content_rejection':str(e)})
 q=fixture('validB');run=signing(q,B,B,wb);assert run.returncode==0,run.stderr;pub.verify_bundle_signature(q,pub.load_release_manifest(q),wv,required=True,expected_fingerprint=B)
 try:pub.verify_bundle_signature(q,pub.load_release_manifest(q),wv,required=True,expected_fingerprint=A);raise AssertionError('wrong signer accepted')
 except RuntimeError as e:assert 'signer mismatch' in str(e)
 q=fixture('wrong-pin');before={n:(q/n).read_bytes() for n in ['btx-release-manifest.json','SHA256SUMS']};run=signing(q,B,A,wb);assert run.returncode!=0 and 'signer mismatch' in run.stderr;assert all((q/n).read_bytes()==b for n,b in before.items());assert not (q/'SHA256SUMS.asc').exists();results.append({'id':'R4','result':'PASS','valid_B_control':True,'pin_rejected':True,'rollback_byte_exact':True})
 try:pub.verify_bundle_signature(p,pub.load_release_manifest(p),we,required=True,expected_fingerprint=A);raise AssertionError('missing key accepted')
 except RuntimeError as e:assert 'signature verification failed' in str(e) and 'No public key' in str(e);results.append({'id':'R5','result':'PASS','rejection':str(e)})
 run=signing(q,sub+'!',A,wa);assert run.returncode==0,run.stderr;pub.verify_bundle_signature(q,pub.load_release_manifest(q),wv,required=True,expected_fingerprint=A);pub.ensure_bundle(q);results.append({'id':'C2','result':'PASS','same_rollback_fixture_retry':True})
except BaseException as e:results.append({'id':'EXECUTION','result':'FAIL','error':str(e)});raise
finally:
 cleanup=[]
 for agent in agents:
  if agent.poll() is None:agent.terminate()
  forced=False
  try:rc=agent.wait(timeout=10)
  except subprocess.TimeoutExpired:agent.kill();rc=agent.wait(timeout=5);forced=True
  cleanup.append({'launcher_pid':agent.pid,'launcher_exit':rc,'forced':forced})
 # GnuPG daemon may fork even when its launcher exits; stop only verified scratch agents.
 owned=subprocess.check_output(['ps','-axo','pid=,command='],text=True)
 for line in owned.splitlines():
  parts=line.strip().split(None,1)
  if len(parts)==2 and parts[1].startswith(str(prefix/'bin/gpg-agent')) and any('--homedir '+str(h) in parts[1] for h in homes):
   os.kill(int(parts[0]),signal.SIGTERM);cleanup.append({'daemon_pid':int(parts[0]),'owned_command_verified':True})
 time.sleep(.2)
 for home in homes:shutil.rmtree(home)

 shutil.rmtree(work)
 ps=subprocess.check_output(['ps','-axo','pid,command'],text=True);remaining=[x for x in ps.splitlines() if 'gpg-agent' in x and str(prefix) in x];cleanupok=not remaining and all(x.get('launcher_exit',0) in [0,-15] for x in cleanup)
 record={'utc':datetime.now(timezone.utc).isoformat(),'results':results,'fingerprints':fingerprints,'cleanup':cleanup,'private_homes_removed':all(not x.exists() for x in homes),'remaining_owned_agents':remaining,'cleanup_ok':cleanupok,'elapsed_s':round(time.monotonic()-began,2),'native_BTX_tests_run':False,'production_keys_used':False,'published':False};(r/'matrix-results.json').write_text(json.dumps(record,indent=2)+'\n');(r/'matrix-raw.json').write_text(json.dumps(raw,indent=2)+'\n');print(json.dumps(record,indent=2))
