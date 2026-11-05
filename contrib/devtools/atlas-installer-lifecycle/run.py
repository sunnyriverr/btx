"""Three real-package association cases in a fresh disposable Windows account."""
from pathlib import Path
import hashlib,json,os,platform,shutil,subprocess,sys,time,uuid,winreg as reg
HERE=Path(__file__).resolve().parent
OUT=Path('atlas-installer-results').resolve()
STATE={'platform':platform.platform(),'controls':[],'restoration':[],'snapshots':[],'commands':[],'errors':[]}
VIEW=reg.KEY_WOW64_64KEY
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check(name,okay,category='controls',**extra):
 STATE[category].append({'name':name,'pass':bool(okay),**extra})
 if category=='controls' and not okay:raise RuntimeError(name)
def tree(key,hive=reg.HKEY_CURRENT_USER):
 try:h=reg.OpenKey(hive,key,0,reg.KEY_READ|VIEW)
 except FileNotFoundError:return None
 with h:
  values={};children={}
  for i in range(reg.QueryInfoKey(h)[1]):
   n,v,t=reg.EnumValue(h,i);values[n]={'type':t,'value':v}
  for i in range(reg.QueryInfoKey(h)[0]):
   n=reg.EnumKey(h,i);children[n]=tree(key+'\\'+n,hive)
  return {'values':values,'children':children}
def write(key,name,value,kind=reg.REG_SZ):
 with reg.CreateKeyEx(reg.HKEY_CURRENT_USER,key,0,reg.KEY_WRITE|VIEW) as h:reg.SetValueEx(h,name,0,kind,value)
def remove(key):
 t=tree(key)
 if t is None:return
 for n in t['children']:remove(key+'\\'+n)
 reg.DeleteKeyEx(reg.HKEY_CURRENT_USER,key,VIEW,0)
def default(key):
 t=tree(key);return None if t is None else t['values'].get('',{}).get('value')
def main():
 if (OUT/'qualification.json').exists():
  build=json.loads((OUT/'qualification.json').read_text());check('qualified retained package',build['qualified_for_lifecycle_test']);STATE['build_qualification']=build['facts']
 else:
  build=json.loads((OUT/'build.json').read_text());check('qualified actual build',build['pass'])
 package=build['package'];STATE['package']=package
 installer=Path(package['installer_path']);check('actual installer identity',sha(installer)==package['installer_sha256'])
 d=package['definitions'];check('actual product identities',d['PRODUCTNAME']=='BTX Atlas' and d['BUNDLEID']=='dev.btx.atlas' and d['INSTALLMODE']=='currentUser' and d['MANUFACTURER']=='btx')
 classes='Software\\Classes\\';ext=classes+'.btx';prog=classes+'BTX Model Resource'
 protocols=[classes+'btx',classes+'btx-p2p'];product='Software\\btx\\BTX Atlas';parent='Software\\btx'
 arp='Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\BTX Atlas'
 runkey='Software\\Microsoft\\Windows\\CurrentVersion\\Run'
 explorer='Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\FileExts\\.btx'
 actualkeys=[ext,prog,*protocols,product,arp]
 original_parent=tree(parent);original_explorer=tree(explorer)
 def webview_state():
  guid='{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'
  return {'HKCU64':tree('Software\\Microsoft\\EdgeUpdate\\Clients\\'+guid),'HKLM64':tree('Software\\Microsoft\\EdgeUpdate\\Clients\\'+guid,reg.HKEY_LOCAL_MACHINE),'HKLM32':tree('Software\\WOW6432Node\\Microsoft\\EdgeUpdate\\Clients\\'+guid,reg.HKEY_LOCAL_MACHINE)}
 STATE['webview_before']=webview_state()
 original_hklm={k:tree(k,reg.HKEY_LOCAL_MACHINE) for k in [ext,prog,*protocols]}
 for k in actualkeys:check('fresh product surface '+k,tree(k) is None)
 run_before=tree(runkey);check('no existing product autostart',run_before is None or 'BTX Atlas' not in run_before['values'])
 installed=Path(os.environ['LOCALAPPDATA'])/'BTX Atlas';check('fresh installed path',not installed.exists())
 appdirs=[Path(os.environ[n])/'dev.btx.atlas' for n in ['APPDATA','LOCALAPPDATA']]
 for f in appdirs:check('fresh appdata '+str(f),not f.exists())
 info=subprocess.check_output(['pwsh','-NoProfile','-Command',"@{desktop=[Environment]::GetFolderPath('DesktopDirectory');programs=[Environment]::GetFolderPath('Programs');atlas_processes=@(Get-Process -Name btx-atlas -ErrorAction SilentlyContinue).Count} | ConvertTo-Json"],text=True)
 STATE['initial_environment']=json.loads(info);check('no running Atlas',STATE['initial_environment']['atlas_processes']==0)
 shortcuts=[Path(STATE['initial_environment'][n])/'BTX Atlas.lnk' for n in ['desktop','programs']]
 for f in shortcuts:check('no existing Atlas shortcut '+str(f),not f.exists())
 token=uuid.uuid4().hex;scratch=Path(os.environ['RUNNER_TEMP'])/('atlas-lifecycle-'+token);scratch.mkdir()
 sentinel=parent+'\\Probe-'+token;runname='AtlasProbe-'+token
 check('sentinel absent',tree(sentinel) is None)
 owned=[];STATE['fixture_token']=token
 try:
  write(sentinel,'preserve','keep-'+token);write(sentinel,'number',321,reg.REG_DWORD);sentinel_before=tree(sentinel)
  write(runkey,runname,'fixture-only-not-executed')
  for folder in appdirs:
   folder.mkdir();(folder/'fixture-only.txt').write_text('keep-'+token)
  def launch(exe,args,label):
   temp=scratch/label;temp.mkdir();observation=OUT/(label+'-process.json')
   start=time.monotonic()
   r=subprocess.run(['pwsh','-NoProfile','-File',str(HERE/'wait-installer.ps1'),'-Executable',str(exe),'-Arguments',args,'-Observation',str(observation)],env=dict(os.environ,TEMP=str(temp),TMP=str(temp)),capture_output=True,timeout=360)
   (OUT/(label+'.log')).write_bytes(r.stdout+b'\nSTDERR\n'+r.stderr)
   STATE['commands'].append({'executable':str(exe),'arguments':args,'exit':r.returncode,'seconds':round(time.monotonic()-start,2),'process_observation':str(observation)})
   check(label+' process tree completed',r.returncode==0 and observation.is_file())
  for case in ['prior','reinstall','later']:
   check(case+' product class absent',tree(prog) is None)
   check(case+' extension reset',tree(ext) is None)
   prior=classes+'AtlasProbe.'+token+'.'+case+'.Previous';later=classes+'AtlasProbe.'+token+'.'+case+'.Later'
   check(case+' prior/later absent',tree(prior) is None and tree(later) is None);owned.extend([prior,later])
   write(prior,'','Previous fixture handler');write(prior+'\\shell\\open\\command','','"'+sys.executable+'" "fixture-prior-only" "%1"')
   write(ext,'',prior.removeprefix(classes));write(ext,'UnrelatedFixture','keep-'+token);write(ext+'\\UnrelatedChild','number',711,reg.REG_DWORD)
   prior_before=tree(prior)
   def snap(stage):
    STATE['snapshots'].append({'case':case,'stage':stage,'keys':{k:tree(k) for k in [*actualkeys,prior,later]},'files':{'binary_exists':(installed/(d['MAINBINARYNAME']+'.exe')).is_file(),'uninstaller_exists':(installed/'uninstall.exe').is_file(),'install_dir_exists':installed.exists()}})
   def install(label):
    check(case+' installer remains identical '+label,sha(installer)==package['installer_sha256'])
    launch(installer,'/S /NS',case+'-'+label)
    check(case+' real class registered '+label,default(ext)=='BTX Model Resource')
    check(case+' actual default install path '+label,default(product)==str(installed))
    check(case+' installed exe identity '+label,sha(installed/(d['MAINBINARYNAME']+'.exe'))==package['binary_sha256'])
    check(case+' real uninstaller '+label,(installed/'uninstall.exe').is_file())
    STATE.setdefault('uninstaller_sha256',{})[case+'-'+label]=sha(installed/'uninstall.exe')
    expected='"'+str(installed/(d['MAINBINARYNAME']+'.exe'))+'" "%1"'
    check(case+' class command '+label,default(prog+'\\shell\\open\\command')==expected)
    for k in protocols:check(case+' protocol command '+k+' '+label,default(k+'\\shell\\open\\command')==expected)
    for f in shortcuts:check(case+' NS suppresses new shortcut '+str(f),not f.exists())
    snap(label)
   snap('before');install('install1')
   if case=='reinstall':install('install2')
   if case=='later':
    write(later,'','Later fixture handler');write(later+'\\shell\\open\\command','','"'+sys.executable+'" "fixture-later-only" "%1"');write(ext,'',later.removeprefix(classes));later_before=tree(later);snap('later-registry-choice')
   launch(installed/'uninstall.exe','/S',case+'-uninstall')
   check(case+' class removed',tree(prog) is None);check(case+' ARP removed',tree(arp) is None)
   check(case+' installed exe removed',not (installed/(d['MAINBINARYNAME']+'.exe')).exists());check(case+' uninstaller removed',not (installed/'uninstall.exe').exists());check(case+' empty installed directory removed',not installed.exists())
   for k in protocols:check(case+' owned protocol removed '+k,tree(k) is None)
   snap('after-uninstall');expected=(later if case=='later' else prior).removeprefix(classes);actual=default(ext)
   check(case+' default restoration',actual==expected,'restoration',expected=expected,actual=actual,dangling_atlas_class=(actual=='BTX Model Resource' and tree(prog) is None))
   check(case+' prior handler untouched',tree(prior)==prior_before)
   if case=='later':check(case+' later handler untouched',tree(later)==later_before)
   t=tree(ext);check(case+' unrelated extension value',t['values']['UnrelatedFixture']=={'type':reg.REG_SZ,'value':'keep-'+token});check(case+' unrelated child',t['children']['UnrelatedChild']['values']['number']=={'type':reg.REG_DWORD,'value':711})
   check(case+' manufacturer sibling unchanged',tree(sentinel)==sentinel_before)
   check(case+' unrelated Run preserved',tree(runkey)['values'][runname]=={'type':reg.REG_SZ,'value':'fixture-only-not-executed'})
   for folder in appdirs:check(case+' appdata retained '+str(folder),(folder/'fixture-only.txt').read_text()=='keep-'+token)
   check(case+' Explorer metadata unchanged',tree(explorer)==original_explorer)
   for k,original in original_hklm.items():check(case+' HKLM association unchanged '+k,tree(k,reg.HKEY_LOCAL_MACHINE)==original)
   # Every selected surface was absent before fixture setup; reset only those owned surfaces.
   for k in [ext,prog,*protocols,product,arp,prior,later]:remove(k)
   check(case+' exact case reset',all(tree(k) is None for k in [*actualkeys,prior,later]));snap('after-fixture-reset')
  STATE['webview_after']=webview_state()
 finally:
  # Only baseline-absent Atlas/fixture keys can be cleaned here; never delete the manufacturer parent recursively.
  if (installed/'uninstall.exe').exists():
   try:launch(installed/'uninstall.exe','/S','failure-cleanup')
   except Exception as exc:STATE['errors'].append('cleanup uninstall '+repr(exc))
  for k in [*actualkeys,*owned,sentinel]:remove(k)
  if original_parent is None and tree(parent)=={'values':{},'children':{}}:remove(parent)
  with reg.OpenKey(reg.HKEY_CURRENT_USER,runkey,0,reg.KEY_SET_VALUE|VIEW) as h:reg.DeleteValue(h,runname)
  if run_before is None and tree(runkey)=={'values':{},'children':{}}:remove(runkey)
  for folder in appdirs:
   (folder/'fixture-only.txt').unlink();folder.rmdir()
  shutil.rmtree(scratch)
  check('final fixture/product registry cleanup',all(tree(k) is None for k in [*actualkeys,*owned,sentinel]))
  check('manufacturer parent restored exactly',tree(parent)==original_parent)
  check('installed directory absent',not installed.exists());check('scratch absent',not scratch.exists())
  check('Run key restored exactly',tree(runkey)==run_before)
try:main()
except Exception as exc:STATE['errors'].append(repr(exc))
finally:
 STATE['controls_pass']=bool(STATE['controls']) and all(x['pass'] for x in STATE['controls']) and not STATE['errors'];STATE['restoration_pass']=len(STATE['restoration'])==3 and all(x['pass'] for x in STATE['restoration']);(OUT/'result.json').write_text(json.dumps(STATE,indent=2)+'\n');print(json.dumps({k:STATE[k] for k in ['controls_pass','restoration_pass','restoration','errors']},indent=2))
sys.exit(0 if STATE['controls_pass'] and STATE['restoration_pass'] else 1)
