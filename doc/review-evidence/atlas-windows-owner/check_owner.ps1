param([Parameter(Mandatory=$true)][string]$Repo,[Parameter(Mandatory=$true)][string]$Out)
$ErrorActionPreference='Stop'
$PSNativeCommandUseErrorActionPreference=$false
New-Item -ItemType Directory -Path $Out -ErrorAction Stop | Out-Null
$root=Join-Path $env:RUNNER_TEMP ('atlas-owner-'+[Guid]::NewGuid().ToString('N'))
$target=Join-Path $root 'fixture.exe'
$user=[Security.Principal.WindowsIdentity]::GetCurrent()
$userSid=$user.User.Value
$admin=([Security.Principal.WindowsPrincipal]$user).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$result=@{status='RUNNING';admin=$admin;platform=[Environment]::OSVersion.VersionString;user_sid=$userSid;cases=@();scripts=@{};fixture=$root}
$failure=$null
function Save-Result { $result | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $Out 'result.json') -Encoding utf8 }
function Snapshot {
 $a=Get-Acl -LiteralPath $target
 $rules=@($a.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]) | ForEach-Object { @{sid=$_.IdentityReference.Value;rights=[int]$_.FileSystemRights;type=$_.AccessControlType.ToString();inherited=$_.IsInherited} })
 return @{owner=$a.GetOwner([Security.Principal.SecurityIdentifier]).Value;sddl=$a.GetSecurityDescriptorSddlForm([Security.AccessControl.AccessControlSections]::All);rules=$rules;sha256=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash}
}
function Check-State([string]$state,[string]$shell,[string]$script,[int]$expected,[bool]$ownerMessage) {
 $before=Snapshot
 $text=@(& $shell -NoProfile -NonInteractive -File $script -Path $target 2>&1 | ForEach-Object { "$_" })
 $rc=$LASTEXITCODE
 $after=Snapshot
 $name=$state+'-'+[IO.Path]::GetFileNameWithoutExtension($shell)+'-'+[IO.Path]::GetFileNameWithoutExtension($script)
 $text | Set-Content -LiteralPath (Join-Path $Out ($name+'.log')) -Encoding utf8
 $result.cases+=@{name=$name;exit=$rc;expected=$expected;before=$before;after=$after;log=($name+'.log')}
 Save-Result
 if($rc -ne $expected){throw "$name returned $rc, expected $expected"}
 if($before.sddl -ne $after.sddl -or $before.sha256 -ne $after.sha256){throw "$name changed fixture ACL/content"}
 if($ownerMessage -and -not (($text -join "`n") -match 'owner: BUILTIN\\Users \(S-1-5-32-545\)')){throw "$name lacked owner diagnostic"}
 if(($text -join "`n") -match 'write grant:'){throw "$name unexpectedly includes an explicit broad write grant"}
}
try {
 if(-not $admin){throw 'NOT_RUN: existing elevated administrator token required'}
 $extract=@'
import pathlib,subprocess,sys,hashlib,json
repo,out=map(pathlib.Path,sys.argv[1:]);records={}
for name,rev in [('baseline','acbf7efb20b1b82da06affdae2ead08068cf743c'),('current','afd6591970e7f8d65871412b9d7cf03b48f30b97')]:
 data=subprocess.check_output(['git','-C',str(repo),'show',rev+':contrib/atlas/check_windows_acl.ps1']);(out/(name+'.ps1')).write_bytes(data);records[name]={'commit':rev,'sha256':hashlib.sha256(data).hexdigest()}
(out/'script-identities.json').write_text(json.dumps(records,indent=2))
'@
 & python -c $extract $Repo $Out
 if($LASTEXITCODE -ne 0){throw 'Script extraction failed'}
 $result.scripts=Get-Content -Raw (Join-Path $Out 'script-identities.json') | ConvertFrom-Json -AsHashtable
 $shells=@((Get-Command powershell.exe).Source,(Get-Command pwsh.exe).Source)
 $result.shell_versions=@{}
 foreach($shell in $shells){$result.shell_versions[$shell]=((& $shell -NoProfile -NonInteractive -Command '$PSVersionTable.PSVersion.ToString()') -join '')}
 New-Item -ItemType Directory -Path $root | Out-Null
 $acl=[Security.AccessControl.DirectorySecurity]::new()
 $acl.SetAccessRuleProtection($true,$false)
 $inherit=[Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [Security.AccessControl.InheritanceFlags]::ObjectInherit
 foreach($sid in @($userSid,'S-1-5-18','S-1-5-32-544') | Select-Object -Unique){
  $rule=[Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($sid),[Security.AccessControl.FileSystemRights]::FullControl,$inherit,[Security.AccessControl.PropagationFlags]::None,[Security.AccessControl.AccessControlType]::Allow)
  $acl.AddAccessRule($rule)
 }
 Set-Acl -LiteralPath $root -AclObject $acl
 Copy-Item -LiteralPath (Join-Path $env:SystemRoot 'System32\notepad.exe') -Destination $target
 & icacls.exe $target /setowner ('*'+$userSid) | Set-Content -LiteralPath (Join-Path $Out 'initial-owner.log') -Encoding utf8
 if($LASTEXITCODE -ne 0){throw 'Could not establish normal fixture owner'}
 $initial=Snapshot
 if($initial.owner -ne $userSid){throw 'Initial owner is not the fixture creator'}
 $result.initial=$initial
 $broad=@('S-1-1-0','S-1-5-32-545','S-1-5-11','S-1-5-4','S-1-5-7','S-1-5-32-546')
 if(@($initial.rules | Where-Object { $_.sid -in $broad }).Count -ne 0){throw 'Fixture has a broad-group ACE'}
 foreach($shell in $shells){Check-State 'normal' $shell (Join-Path $Out 'current.ps1') 0 $false}
 & icacls.exe $target /setowner '*S-1-5-32-545' | Set-Content -LiteralPath (Join-Path $Out 'set-owner.log') -Encoding utf8
 if($LASTEXITCODE -ne 0){throw 'Existing token could not set fixture owner'}
 $changed=Snapshot
 if($changed.owner -ne 'S-1-5-32-545'){throw 'Users owner SID not established'}
 if((ConvertTo-Json $initial.rules -Compress) -ne (ConvertTo-Json $changed.rules -Compress) -or $initial.sha256 -ne $changed.sha256){throw 'Owner transition changed DACL/content'}
 foreach($shell in $shells){
  Check-State 'users-owner' $shell (Join-Path $Out 'baseline.ps1') 0 $false
  Check-State 'users-owner' $shell (Join-Path $Out 'current.ps1') 1 $true
 }
 & icacls.exe $target /setowner ('*'+$userSid) | Set-Content -LiteralPath (Join-Path $Out 'restore-owner.log') -Encoding utf8
 if($LASTEXITCODE -ne 0){throw 'Fixture owner restoration failed'}
 $restored=Snapshot
 if($initial.sddl -ne $restored.sddl -or $initial.sha256 -ne $restored.sha256){throw 'Restored fixture differs'}
 foreach($shell in $shells){Check-State 'restored' $shell (Join-Path $Out 'current.ps1') 0 $false}
 $result.status='PASS'
} catch {$failure=$_; $result.status='FAILED_OR_NOT_RUN';$result.error="$($_.Exception.Message)"}
finally {
 if(Test-Path -LiteralPath $target){
  & icacls.exe $target /setowner ('*'+$userSid) | Out-Null
  $result.cleanup_restore_exit=$LASTEXITCODE
 }
 if(Test-Path -LiteralPath $root){Remove-Item -LiteralPath $root -Recurse -Force}
 $result.fixture_removed= -not (Test-Path -LiteralPath $root)
 Save-Result
}
if($failure){throw $failure}
if(-not $result.fixture_removed -or $result.cleanup_restore_exit -ne 0){$result.status='FAILED_CLEANUP'; Save-Result; throw 'Fixture cleanup incomplete'}
Write-Output 'PASS: normal -> Users owner -> restored; checker remains read-only; PS5.1 and PS7'
