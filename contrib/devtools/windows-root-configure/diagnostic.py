from pathlib import Path
import os,sys,json,subprocess,shutil,hashlib
import restore_support as h
s=h.s;R=h.R;E=h.E;B=h.B;ROOT=h.ROOT

def command(label,args,env=None,input_bytes=None):
 row={'label':label,'argv':[str(a)for a in args],'environment':'parent-style LANG/SystemRoot only'if env is not None else'inherited runner','stdin_hex':input_bytes.hex()if input_bytes is not None else None};R.setdefault('diagnostic_cases',[]).append(row);s.save()
 p=subprocess.Popen(row['argv'],cwd=B/'bin',env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 try:out,err=p.communicate(input_bytes,timeout=20)
 except subprocess.TimeoutExpired:
  row['timeout']=True;subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True);out,err=p.communicate(timeout=15)
 (E/(label+'-stdout.bin')).write_bytes(out);(E/(label+'-stderr.bin')).write_bytes(err);row.update(exit=p.returncode,stdout_hex=out.hex(),stderr=err.decode(errors='replace'),stdout_sha256=hashlib.sha256(out).hexdigest(),stderr_sha256=hashlib.sha256(err).hexdigest())
 if input_bytes==b'PING\n':
  # Reproduce Transport's framing rule literally: it pops only the final LF.
  at=out.find(b'\n');reply=out[:-1]if at==len(out)-1 and at>=0 and b'\0'not in out else None
  row.update(node_transport_reply_hex=reply.hex()if reply is not None else None,node_exact_ready_match=reply==b'READY BTX_GUARD/1',human_line_ready=out.rstrip(b'\r\n')==b'READY BTX_GUARD/1')
 s.save();return row

def acl_snapshot(path):
 ps="$p='"+str(path).replace("'","''")+"';if(Test-Path -LiteralPath $p){$a=Get-Acl -LiteralPath $p;[pscustomobject]@{Path=$p;Owner=$a.Owner;SDDL=$a.Sddl;Protected=$a.AreAccessRulesProtected}|ConvertTo-Json -Compress}"
 p=subprocess.run(['powershell','-NoProfile','-Command',ps],capture_output=True,text=True,timeout=20)
 return {'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr}

def private_directory(path):
 ps="$ErrorActionPreference='Stop';$p='"+str(path).replace("'","''")+"';$sid=[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value;New-Item -ItemType Directory -Path $p|Out-Null;& icacls $p /setowner ('*'+$sid);if($LASTEXITCODE){throw 'setowner'};& icacls $p /grant:r ('*'+$sid+':(OI)(CI)F') '*S-1-5-18:(OI)(CI)F';if($LASTEXITCODE){throw 'grant'};& icacls $p /inheritance:r;if($LASTEXITCODE){throw 'inheritance'};Get-Acl $p|Select-Object Owner,Sddl,AreAccessRulesProtected|ConvertTo-Json -Compress"
 p=subprocess.run(['powershell','-NoProfile','-Command',ps],capture_output=True,text=True,timeout=20);(E/'private-directory-preparation.log').write_text(p.stdout+'\n'+p.stderr);assert p.returncode==0,'Private control fixture setup failed';return acl_snapshot(path)

def run():
 assert R['status']=='RESTORED_VERIFIED';assert not h.processes();root=Path('D:/gd'+os.environ['GITHUB_RUN_ID']);assert not root.exists();root.mkdir();R['runtime_root']=str(root);R['diagnostic_cases']=[];R['directory_controls']={};R['status']='GUARD_DIAGNOSIS_RUNNING';s.save()
 try:
  bare=command('bare-guard',[B/'bin/btx-guardd.exe','--stdio'],input_bytes=b'PING\n')
  assert bare['exit']==0 and bare['human_line_ready']and not bare.get('timeout'),'Bare guard failed; isolate executable/stdio before service assumptions'
  fresh=root/'fresh-parent'/'security'
  command('fresh-security-guard',[B/'bin/btx-guardd.exe','--stdio','--security-dir',fresh],input_bytes=b'PING\n');R['directory_controls']['fresh']=acl_snapshot(fresh)
  command('fresh-security-inspect',[B/'bin/btx-security.exe','inspect','--root',root/'inspect-parent'/'security'])
  controlled=root/'private-parent'/'security';controlled.parent.mkdir();R['directory_controls']['owner_private']=private_directory(controlled)
  command('private-security-inspect',[B/'bin/btx-security.exe','inspect','--root',controlled])
  command('private-security-guard',[B/'bin/btx-guardd.exe','--stdio','--security-dir',controlled],input_bytes=b'PING\n')
  command('private-security-guard-minenv',[B/'bin/btx-guardd.exe','--stdio','--security-dir',controlled],env={'LANG':'C','SystemRoot':os.environ['SystemRoot']},input_bytes=b'PING\n')
  R['status']='DIAGNOSTIC_OBSERVATIONS_COMPLETE';s.save()
 finally:
  leftover=h.processes();R['remaining_before_cleanup']=leftover
  if leftover:s.quiesce()
  assert not h.processes();R['process_cleanup_verified']=not leftover
  if root.exists():shutil.rmtree(root)
  R['runtime_removed']=not root.exists();s.save()
 assert R['process_cleanup_verified']and all(not c.get('timeout')for c in R['diagnostic_cases'])

try:
 stage=sys.argv[1]
 if stage=='prepare':h.prepare()
 elif stage=='run':run()
 elif stage=='verify':h.verify()
 else:raise ValueError(stage)
except BaseException as e:R.setdefault('errors',[]).append({'stage':sys.argv[1],'error':repr(e)});raise
finally:s.save()
