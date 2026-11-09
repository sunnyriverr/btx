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
 ps="""$ErrorActionPreference='Stop';$p='PATH';$sid=[System.Security.Principal.WindowsIdentity]::GetCurrent().User;$system=[System.Security.Principal.SecurityIdentifier]::new('S-1-5-18');New-Item -ItemType Directory -Path $p|Out-Null;$acl=[System.Security.AccessControl.DirectorySecurity]::new();$acl.SetOwner($sid);$acl.SetAccessRuleProtection($true,$false);$inherit=[System.Security.AccessControl.InheritanceFlags]'ContainerInherit,ObjectInherit';$prop=[System.Security.AccessControl.PropagationFlags]::None;$allow=[System.Security.AccessControl.AccessControlType]::Allow;$full=[System.Security.AccessControl.FileSystemRights]::FullControl;foreach($principal in @($sid,$system)){$acl.AddAccessRule([System.Security.AccessControl.FileSystemAccessRule]::new($principal,$full,$inherit,$prop,$allow))};[System.IO.Directory]::SetAccessControl($p,$acl);$a=Get-Acl -LiteralPath $p;$owner=$a.GetOwner([System.Security.Principal.SecurityIdentifier]).Value;$rules=@($a.GetAccessRules($true,$true,[System.Security.Principal.SecurityIdentifier]));if($owner -ne $sid.Value -or -not $a.AreAccessRulesProtected -or $rules.Count -ne 2){throw 'owner/protection/rulecount mismatch'};foreach($r in $rules){if($r.IdentityReference.Value -notin @($sid.Value,'S-1-5-18') -or $r.AccessControlType -ne 'Allow' -or $r.IsInherited -or ($r.FileSystemRights -band $full) -ne $full){throw 'unexpected ACL rule'}};[pscustomobject]@{Owner=$owner;CurrentUser=$sid.Value;SDDL=$a.Sddl;Protected=$a.AreAccessRulesProtected;Rules=@($rules|Select-Object IdentityReference,FileSystemRights,IsInherited)}|ConvertTo-Json -Depth 4 -Compress""".replace('PATH',str(path).replace("'","''"))
 p=subprocess.run(['powershell','-NoProfile','-Command',ps],capture_output=True,text=True,timeout=20);(E/'private-directory-preparation.log').write_text(p.stdout+'\n'+p.stderr);assert p.returncode==0,'Exact private ACL fixture validation failed';return json.loads(p.stdout)

def run():
 assert R['status']=='RESTORED_VERIFIED';assert not h.processes();root=Path('D:/gdc'+os.environ['GITHUB_RUN_ID']);assert not root.exists();root.mkdir();R['runtime_root']=str(root);R['diagnostic_cases']=[];R['directory_controls']={};R['status']='GUARD_DIAGNOSIS_RUNNING';s.save()
 try:
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
