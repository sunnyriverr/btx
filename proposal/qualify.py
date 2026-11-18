"""One bounded retained-cache build; identical native regression before/after."""
import hashlib,json,os,selectors,shutil,signal,subprocess,sys,time
from pathlib import Path
from results import validate
from read_suite import validate as cloud_suite
w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'records';p=w/'proposal';src=w/'product';build=w/'gui-pilot-runtime/qtbuild';ref=w/'current-reference'
base='23ee567ea8a2d9cad8ca3264f8793e8371b3eb93';r={'complete':False,'source':base,'current_applicability':'a97af7b3f379e33e3ec65db948468d875ade2841','commands':[]};deadline=time.monotonic()+30*60

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save():(out/'qualification.json').write_text(json.dumps(r,indent=2)+'\n')
def run(cmd,label,limit,cwd=None,allowed=(0,)):
    start=time.monotonic();proc=subprocess.Popen([str(x)for x in cmd],cwd=cwd or w,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
    chunks=[];timed=False
    with (out/(label+'.log')).open('wb')as log:
        sel=selectors.DefaultSelector();sel.register(proc.stdout,selectors.EVENT_READ)
        try:
            while sel.get_map():
                for key,_ in sel.select(1):
                    data=os.read(key.fileobj.fileno(),65536)
                    if not data:sel.unregister(key.fileobj);continue
                    chunks.append(data);log.write(data);log.flush();sys.stdout.buffer.write(data);sys.stdout.buffer.flush()
                if proc.poll() is None and (time.monotonic()-start>limit or time.monotonic()>deadline or shutil.disk_usage(w).free<3*1024**3):
                    timed=True;os.killpg(proc.pid,signal.SIGTERM)
                    try:proc.wait(10)
                    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
            proc.wait()
        finally:sel.close()
    r['commands'].append({'label':label,'exit':proc.returncode,'seconds':time.monotonic()-start,'timeout_or_disk':timed});save()
    assert not timed and proc.returncode in allowed,(label,proc.returncode)
    return proc.returncode,b''.join(chunks).decode(errors='replace')

try:
    assert json.loads((out/'staging.json').read_text())['complete']
    binary=json.loads((out/'current-binary.json').read_text());assert binary['complete']
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ref,text=True).strip()==base
    tracked=[n for n in subprocess.check_output(['git','ls-files','-z'],cwd=ref,text=True).split('\0')if n]
    changed=[]
    for name in tracked:
        a=ref/name;b=src/name
        same=(b.is_symlink()and os.readlink(b)==os.readlink(a))if a.is_symlink()else(b.is_file()and not b.is_symlink()and sha(a)==sha(b)and (a.stat().st_mode&0o111)==(b.stat().st_mode&0o111))
        if same:continue
        b.parent.mkdir(parents=True,exist_ok=True)
        if b.is_symlink()or b.is_file():b.unlink()
        if a.is_symlink():b.symlink_to(os.readlink(a))
        else:shutil.copy2(a,b);os.utime(b,None)
        changed.append(name)
    for name in tracked:
        a=ref/name;b=src/name
        assert (b.is_symlink()and os.readlink(a)==os.readlink(b))if a.is_symlink()else sha(a)==sha(b),name
    r['exact_base_overlay_changed']=changed
    assert sha(src/'src/modelnet/helper.cpp')==sha(p/'baseline-helper.cpp')
    run(['git','apply',p/'candidate.patch'],'patch-application-check',30,ref)
    assert sha(ref/'src/modelnet/helper.cpp')==sha(p/'candidate-helper.cpp')
    assert sha(ref/'contrib/devtools/test_modelnet_cloud_responsiveness.py')==sha(p/'regression.py')
    r['patch_postimages_verified']=True
    test=src/'contrib/devtools/test_modelnet_cloud_responsiveness.py';test.write_bytes((p/'regression.py').read_bytes());test.chmod(0o755)
    os.environ['BTX_OPENSSL']=str(w/'gui-pilot-runtime/openssl/bin/openssl')
    run([os.environ['BTX_OPENSSL'],'version'],'openssl',30)
    def native(name,helper,expected_exit):
        code,_=run(['python3','-B',test,'--helper',helper,'--out',out/name],name,120,allowed=(expected_exit,))
        result=json.loads((out/name/'result.json').read_text());validate(result,name);r[name]=result;r[name+'_test_sha256']=sha(test);save()
    baseline=w/'current-helper/btx-modeld';assert sha(baseline)==binary['helper_sha256']
    saved=p/'saved-baseline.json'
    assert sha(saved)=='2245a0f9757bccb3f6c477294d9d49c975893747687c3f9656d14aabb0f24e5d'
    result=json.loads(saved.read_text());validate(result,'baseline')
    assert result['helper_sha256']==sha(baseline)
    assert sha(test)=='ae71ae5a6356f3a54b4954486136c032b163286c7c430fd310486282db2663e1'
    r['baseline']=result;r['baseline_test_sha256']=sha(test);r['baseline_reused_from_run']=44274288368;save()
    # Only after the baseline fixture and all healthy controls are admitted.
    shutil.copy2(p/'candidate-helper.cpp',src/'src/modelnet/helper.cpp');os.utime(src/'src/modelnet/helper.cpp',None)
    cmake=src/'src/test/CMakeLists.txt';cmake.write_text(cmake.read_text()+(p/'target.cmake').read_text())
    run(['/usr/local/bin/cmake','-S',src,'-B',build,'-DCMAKE_SUPPRESS_REGENERATION=ON'],'configure',150)
    _,text=run(['ninja','-n','btx-modeld','s2_cloud_control_tests'],'dry-run',90,build)
    actions=[line for line in text.splitlines()if line.startswith('[')];r['planned_actions']=len(actions);save()
    assert 0<len(actions)<=64 and any('helper.cpp.o'in line for line in actions)and any('modelnet_cloud_tests.cpp.o'in line for line in actions),'unexpected build plan'
    run(['ninja','-j2','btx-modeld','s2_cloud_control_tests'],'candidate-build',1100,build)
    retained=w/'retained-binaries';retained.mkdir(exist_ok=True)
    helper=build/'bin/btx-modeld';unit=build/'bin/s2_cloud_control_tests'
    shutil.copy2(helper,retained/'btx-modeld');shutil.copy2(unit,retained/'s2_cloud_control_tests')
    r['candidate_helper_sha256']=sha(helper);r['candidate_source_sha256']=sha(src/'src/modelnet/helper.cpp');save()
    native('candidate',helper,0)
    assert r['baseline_test_sha256']==r['candidate_test_sha256']
    xml=out/'cloud-suite.xml'
    code,_=run([unit,'--run_test=modelnet_cloud_tests','--logger=JUNIT,all,'+str(xml),'--report_level=detailed'],'cloud-suite',180)
    suite,normalized=cloud_suite(xml.read_text(),code);(out/'cloud-suite.normalized.xml').write_text(normalized);r['cloud_suite']=suite;save()
    cases=['doctor_host_preview_share_transfers_alias','show_export_open_unhost_empty_search','mirror_policy_and_native_file_stream_hello','setcloudstorage_rejects_link_local_flag_and_secret_shaped_ref','import_into_a_fresh_helper_keeps_the_saved_policy','rejected_policy_save_keeps_live_settings_and_allows_retry','saved_policy_quota_matches_catalog_normalization']
    for case in cases:
        code,text=run([unit,'--run_test=modelnet_first_run_tests/'+case,'--log_level=test_suite','--report_level=detailed'],'first-run-'+case,120)
        assert ('Entering test case "'+case+'"')in text and ('Leaving test case "'+case+'"')in text
    r['first_run_cases']=cases;r['complete']=True;save()
except Exception:
    import traceback;r['error']=traceback.format_exc();save();raise
finally:
    if r.get('candidate_helper_sha256'):
        try:
            from checkpoint import create
            m=create(w,w/'cloud-control-checkpoint',{'source':base,'cloud_control_candidate':True,'qualification_complete':r['complete'],'current_source_applicability':r['current_applicability']},reserve=int(1.25*1024**3))
            r['checkpoint_sha256']=m['archive_sha256']
        except Exception as e:r['checkpoint_error']=repr(e)
    save()
