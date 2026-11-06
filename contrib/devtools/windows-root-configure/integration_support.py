"""Incremental PR411 integration. Exact baseline validation precedes source delta."""
from pathlib import Path
import os,sys,json,hashlib,subprocess,time,datetime,shutil,re
import checkpoint
P=Path(__file__).resolve().parent;ROOT=Path(os.environ['BTX_NATIVE_ROOT'])
SOURCE=Path(os.environ['GITHUB_WORKSPACE'])/'btx';BUILD=ROOT/'project-build';E=ROOT/'evidence'
BASE='666673a3153225ba264c7870e0e82e354df86765';TARGET='362c36b2fda0f73741c06c4bcb090153fea38a08'
STATE=E/'integration.json';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
R=json.loads(STATE.read_text()) if STATE.exists() else {'base':BASE,'target':TARGET,'scope':'Incremental published PR411 candidate integration; not accepted stock source or clean rebuild','status':'SETUP','commands':[],'node_linked':False,'unit_built':False,'unit_invoked':False,'process_active':False}
def save():
    R['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();STATE.write_text(json.dumps(R,indent=2)+'\n')
def resources():
    import ctypes
    class Mem(ctypes.Structure):
        _fields_=[('length',ctypes.c_uint32),('load',ctypes.c_uint32)]+[(x,ctypes.c_uint64) for x in ['total_phys','avail_phys','total_page','avail_page','total_virtual','avail_virtual','avail_extended']]
    m=Mem();m.length=ctypes.sizeof(m);assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return {'disk_free':shutil.disk_usage(ROOT).free,'available_ram':m.avail_phys,'total_ram':m.total_phys,'cpus':os.cpu_count()}
def run(label,cmd,timeout,cwd=SOURCE):
    log=E/(label+'.log');start=time.monotonic();R['active_command']=label;save()
    with log.open('wb') as f:
        proc=subprocess.Popen(cmd,cwd=cwd,stdout=f,stderr=subprocess.STDOUT);R['process_active']=True;save()
        reason=None;bucket=-1
        try:
            while proc.poll() is None:
                elapsed=time.monotonic()-start
                if elapsed>timeout:reason='TIME_BUDGET'
                if label not in ['base-fetch','base-checkout','bundle-verify','bundle-fetch','candidate-checkout']:
                    s=resources()
                    if s['disk_free']<2*1024**3 or s['available_ram']<1024**3:reason='RESOURCE_BUDGET'
                    if int(elapsed)//30>bucket:
                        bucket=int(elapsed)//30
                        if label=='candidate-unit-build':
                            try:
                                with log.open('rb')as progress:
                                    progress.seek(0,2);size=progress.tell();progress.seek(max(0,size-65536));tail=progress.read().decode(errors='replace')
                                match=re.findall(r'\[(\d+)/(\d+)\]',tail);s['log_bytes']=size
                                if match:s['last_ninja_step']='/'.join(match[-1])
                            except OSError:pass
                        R.setdefault('samples',[]).append({'command':label,'seconds':round(elapsed),**s});save();print(label,round(elapsed),s,flush=True)
                if reason:
                    z=subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True);(E/(label+'-cleanup.log')).write_bytes(z.stdout+z.stderr)
                    R['cleanup_confirmed']=z.returncode==0;proc.wait(timeout=30);break
                time.sleep(2)
        except BaseException:
            z=subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True);R['cleanup_confirmed']=z.returncode==0;proc.wait(timeout=30);raise
        finally:R['process_active']=False
    R['active_command']=None;row={'label':label,'command':cmd,'cwd':str(cwd),'exit':proc.returncode,'seconds':round(time.monotonic()-start,2),'log_sha256':sha(log),'budget_stop':reason};R['commands'].append(row);save()
    print(label,proc.returncode,log.read_text(errors='replace')[-7000:],flush=True)
    if reason:raise RuntimeError(label+' stopped: '+reason)
    return proc.returncode
def need(label,cmd,timeout,cwd=SOURCE):
    if run(label,cmd,timeout,cwd):raise RuntimeError(label+' failed; original log retained')
def catalog(expected,label):
    assert subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD'],text=True).strip()==expected
    entries={}
    for row in subprocess.check_output(['git','-C',str(SOURCE),'ls-tree','-rz','--full-tree',expected]).split(b'\0'):
        if not row:continue
        meta,name=row.split(b'\t',1);mode,kind,oid=meta.decode().split();assert kind=='blob';name=name.decode();f=SOURCE/name
        if mode=='120000':
            expected_bytes=subprocess.check_output(['git','-C',str(SOURCE),'cat-file','blob',oid]);data=os.readlink(f).replace('\\','/').encode() if f.is_symlink() else f.read_bytes();assert data==expected_bytes
            entries[name]={'git_mode':mode,'git_blob':oid,'target':data.decode()};continue
        assert not f.is_symlink();data=f.read_bytes();assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==oid,name
        entries[name]={'git_mode':mode,'git_blob':oid,'working_sha256':hashlib.sha256(data).hexdigest()}
    value={'head':expected,'files':entries};(E/(label+'-candidate-source.json')).write_text(json.dumps(value,indent=2)+'\n');return value
def owned_processes():
    # Only this ephemeral job's built programs or short unit-data path qualify.
    prefix=str(BUILD/'bin').replace("'","''");unit=R.get('unit_data','__no_unit_data__').replace("'","''")
    ps="$x=@(Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and $_.ProcessId -ne "+str(os.getpid())+" -and (($_.ExecutablePath -and $_.ExecutablePath.StartsWith('"+prefix+"',[StringComparison]::OrdinalIgnoreCase)) -or ($_.CommandLine -and $_.CommandLine.Contains('"+unit+"'))) } | Select-Object ProcessId,ExecutablePath,CommandLine); ConvertTo-Json -InputObject $x -Compress"
    return json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',ps],text=True))
def quiesce():
    rows=owned_processes();R['owned_processes_after_execution']=rows
    if rows:
        R['status']='OWNED_CHILDREN_REMAINED'
        for row in rows:
            z=subprocess.run(['taskkill','/PID',str(row['ProcessId']),'/T','/F'],capture_output=True);(E/('owned-cleanup-'+str(row['ProcessId'])+'.log')).write_bytes(z.stdout+z.stderr)
        assert not owned_processes(),'Owned process cleanup unconfirmed'
    R['process_quiescence_confirmed']=True;save()
def build():
    validated=json.loads((E/'verified-resume-result.json').read_text());setup=json.loads((E/'result.json').read_text())
    assert validated['source']==BASE and validated['all_commands_identical_to_original'] and validated['command_changed_objects']==0 and validated['stale_deps']==0
    assert validated['restore']['files_verified']==10094
    before=catalog(BASE,'baseline')
    need('candidate-fetch',['git','-C',str(SOURCE),'fetch','--no-tags','--depth=2','https://github.com/sunnyriverr/btx.git',TARGET],120)
    assert subprocess.check_output(['git','-C',str(SOURCE),'rev-parse',TARGET+'^'],text=True).strip()==BASE
    changed=subprocess.check_output(['git','-C',str(SOURCE),'diff','--name-only',BASE,TARGET],text=True).splitlines();assert changed==['src/modelnet/capability_runtime.cpp']
    need('candidate-checkout',['git','-C',str(SOURCE),'checkout','--detach',TARGET],60)
    after=catalog(TARGET,'before');assert set(before['files'])==set(after['files'])
    delta=[k for k in before['files']if before['files'][k]!=after['files'][k]];assert delta==changed
    assert sha(SOURCE/changed[0])=='0fedd51d96a7cf81eb791e55b5a092c9c27994317814b4b23b5a307a124dbd60'
    R['source_delta']=delta;R['configured_inputs_unchanged']=True;R['candidate_catalog_sha256']=sha(E/'before-candidate-source.json')
    R['profile']={'source':TARGET,'actual_baseline_profile':setup['profile'],'original_cached_profile':validated['original_profile'],'permitted_host_transition':validated['profile_transition'],'configuration_manifest_sha256':sha(BUILD/'build.ninja'),'compile_commands_sha256':sha(BUILD/'compile_commands.json'),'integration_script_sha256':sha(P/'integration.py'),'kind':'explicit one-C++-file incremental candidate; no configuration-input delta'}
    R['initial_resources']=resources();assert R['initial_resources']['disk_free']>6*1024**3 and R['initial_resources']['available_ram']>3*1024**3;save()
    manifest=E/'verified-resume.ninja';assert sha(manifest)==sha(BUILD/'build.ninja')
    common=['ninja','-C',str(BUILD),'-f',str(manifest)]
    need('candidate-node-plan',common+['-d','explain','-n','btxd'],120)
    text=(E/'candidate-node-plan.log').read_text(errors='replace');steps=re.findall(r'^\[(\d+)/(\d+)\]',text,re.M)
    R['node_planned_steps']=int(steps[-1][1])if steps else 0
    R['node_command_invalidations']=text.count('ninja explain: command line changed for ')
    assert R['node_command_invalidations']==0 and 0<R['node_planned_steps']<150,'Unexpected broad rebuild; stop before compilation'
    R['status']='CANDIDATE_BUILDING';save()
    code=run('candidate-node-build',common+['--verbose','-j','4','-k','1','btxd'],1800)
    R['node_build_exit']=code
    if code:R['status']='NODE_BUILD_FAILURE';raise RuntimeError('Node compiler/link blocker; units not reached')
    exe=BUILD/'bin/btxd.exe';R['node_binary_sha256']=sha(exe);R['node_linked']=True
    need('candidate-node-imports',['dumpbin','/dependents',str(exe)],60);need('candidate-node-version',[str(exe),'-version'],30)
    assert sha(exe)==R['node_binary_sha256']
    header=BUILD/'src/bitcoin-build-info.h';R['build_info_text']=header.read_text();assert TARGET[:7] in R['build_info_text'] and re.search(r'BUILD_GIT_DIRTY\s+0',R['build_info_text'])
    R['status']='NODE_LINKED_UNITS_BUILDING';save()
    need('candidate-unit-plan',common+['-n','test_btx'],120)
    code=run('candidate-unit-build',common+['--verbose','-j','4','-k','1','test_btx'],5400);R['unit_build_exit']=code
    if code:R['status']='UNIT_BUILD_FAILURE';raise RuntimeError('Maintained unit target compiler/link blocker')
    unit=BUILD/'bin/test_btx.exe';R['unit_binary_sha256']=sha(unit);R['unit_built']=True
    need('candidate-unit-inventory',[str(unit),'--list_content'],60)
    data=Path('D:/bu'+os.environ['GITHUB_RUN_ID']);assert not data.exists();data.mkdir();R['unit_data']=str(data);save()
    R['unit_invoked']=True
    code=run('candidate-unit-run',[str(unit),'--log_level=error','--report_level=detailed','--catch_system_errors=yes','--','-testdatadir='+str(data)],3600);R['unit_exit']=code
    text=(E/'candidate-unit-run.log').read_text(errors='replace');match=re.search(r'Running (\d+) test cases?',text);R['unit_cases_started']=int(match.group(1))if match else 0
    assert sha(unit)==R['unit_binary_sha256'];R['status']='CANDIDATE_NODE_AND_UNITS_PASS' if code==0 and R['unit_cases_started']>0 else 'UNIT_RUN_FAILURE'
    quiesce()
    if R['status']!='CANDIDATE_NODE_AND_UNITS_PASS':raise RuntimeError('Unit invocation did not qualify a pass')
def retain():
    assert not R['process_active'] and R.get('cleanup_confirmed',True)
    if not R.get('profile'):raise RuntimeError('No candidate build state to retain')
    quiesce();current=catalog(TARGET,'retained');original=json.loads((E/'before-candidate-source.json').read_text());assert current==original
    R['checkpoint_capture']=checkpoint.capture(ROOT,SOURCE,R['profile'],current,{'status':R['status'],'node_exit':R.get('node_build_exit'),'unit_build_exit':R.get('unit_build_exit'),'unit_exit':R.get('unit_exit')})
    shutil.copyfile(BUILD/'btx-checkpoint.json',E/'candidate-checkpoint.json');R['objects_retained']=sum(x.endswith('.obj')for x in json.loads((BUILD/'btx-checkpoint.json').read_text())['files']);save()
    key=hashlib.sha256(json.dumps(R['profile'],sort_keys=True).encode()).hexdigest();R['candidate_checkpoint_key']=key;save()
    with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8')as f:f.write('checkpoint_valid=true\ncheckpoint_key='+key+'\n')
