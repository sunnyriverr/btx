"""Exact generated test-fixture pairs, followed by the maintained unit target.
Uses the verified candidate checkpoint without reconfiguring or editing Ninja logs.
"""
from pathlib import Path
import os,sys,json,hashlib,subprocess,shutil,re
import checkpoint
import integration_support as s
P=Path(__file__).resolve().parent;ROOT=s.ROOT;SOURCE=s.SOURCE;BUILD=s.BUILD;E=s.E
I=json.loads((P/'fixture-inputs.json').read_text());BASE=I['cached_source'];TARGET=I['integration_commit']
s.STATE=E/'fixtures.json';s.R=json.loads(s.STATE.read_text()) if s.STATE.exists() else {'base':BASE,'target':TARGET,'status':'SETUP','commands':[],'process_active':False,'scope':'Test-only fixture delta composed with PR411; not accepted stock source'}
R=s.R;sha=s.sha

def differences(a,b,prefix=''):
    out={}
    for k in sorted(set(a)|set(b)):
        x,y=a.get(k),b.get(k)
        if isinstance(x,dict) and isinstance(y,dict):out.update(differences(x,y,prefix+k+'.'))
        elif x!=y:out[prefix+k]=[x,y]
    return out

def metadata():
    names=['CMakeCache.txt','compile_commands.json','build.ninja','CMakeFiles/rules.ninja','.ninja_log','.ninja_deps']
    return {str(f.relative_to(BUILD)):sha(f) for f in list(BUILD.rglob('*.h'))+[BUILD/n for n in names] if f.is_file()}

def prepare():
    setup=json.loads((E/'result.json').read_text());assert all(setup['stages'].get(k)=='COMPLETE' for k in ['openssl','vcpkg','profile'])
    marker=BUILD/'btx-checkpoint.json';assert sha(marker)==I['checkpoint_sha256'];cp=json.loads(marker.read_text());assert cp['profile']['source']==BASE
    diff=differences(cp['profile']['actual_baseline_profile'],setup['profile']);allowed=json.loads((P/'profile-transition.json').read_text())['allowed_differences']
    assert not diff or diff==allowed,diff
    assert subprocess.check_output(['ninja','--version'],text=True).strip()=='1.13.2'
    s.need('cached-source-fetch',['git','-C',str(SOURCE),'fetch','--no-tags','--depth=2','https://github.com/sunnyriverr/btx.git',BASE],120)
    s.need('cached-source-checkout',['git','-C',str(SOURCE),'checkout','--detach',BASE],60)
    catalog=s.catalog(BASE,'cached');assert catalog==cp['source_catalog'];restored=checkpoint.restore(ROOT,SOURCE,cp['profile'],catalog);assert restored['restored'] and restored['files_verified']==I['cached_files']
    commands=json.loads((BUILD/'compile_commands.json').read_text());assert hashlib.sha256(json.dumps(commands,sort_keys=True,separators=(',',':')).encode()).hexdigest()==I['commands_canonical_sha256']
    for n,d in I['configuration_hashes'].items():assert sha(BUILD/n)==d,n
    cache=(BUILD/'CMakeCache.txt').read_text()
    for f in ['WITH_MODELNET:BOOL=ON','BUILD_TESTS:BOOL=ON','ENABLE_WALLET:BOOL=ON','WITH_ZMQ:BOOL=ON']:assert f in cache
    frozen=E/'fixture-resume.ninja';shutil.copyfile(BUILD/'build.ninja',frozen)
    R.update(restore=restored,actual_profile=setup['profile'],cached_profile=cp['profile'],host_transition=diff,source_catalog=catalog,cmake_reconfigured=False)
    s.need('fixture-initial-node-plan',['ninja','-C',str(BUILD),'-f',str(frozen),'-d','explain','-n','btxd'],120)
    txt=(E/'fixture-initial-node-plan.log').read_text(errors='replace');assert 'command line changed for' not in txt and 'stored deps info out of date' not in txt
    R['generated_inputs_before_pair']=metadata();R['status']='PAIRS_READY';s.save()

def rows_for(names):
    commands=json.loads((BUILD/'compile_commands.json').read_text());out=[]
    for n in names:
        rows=[r for r in commands if r['file'].replace('\\','/').endswith('/src/test/'+n) and '/test_btx.dir/' in r['output'].replace('\\','/')];assert len(rows)==1,(n,len(rows))
        r=rows[0];assert Path(r['directory']).resolve()==BUILD.resolve();out.append((n,r))
    return out

def batch(stage,rows):
    out=[]
    for name,row in rows:
        label=stage+'-'+name.removesuffix('.cpp');rc=s.run(label,row['command'],240,BUILD);log=E/(label+'.log');txt=log.read_text(errors='replace')
        out.append({'file':name,'command':row,'exit':rc,'log':log.name,'log_sha256':sha(log),'env_diagnostics':bool(re.search(r"undeclared identifier ['\"](?:setenv|unsetenv)|(?:setenv|unsetenv).*identifier not found",txt)), 'opaque_diagnostics':bool(re.search(r"expanded from macro ['\"]OPAQUE['\"]",txt)),'object_sha256':sha(Path(row['output'])) if rc==0 else None});R[stage]=out;s.save()
    return out

def controls():
    row=rows_for(['matmul_matrix_tests.cpp'])[0][1];text=(SOURCE/'src/test/util/shielded_v2_egress_fixture.h').read_text();includes='\n'.join(l for l in text.splitlines() if l.startswith('#include '))
    for defined in [True,False]:
        f=E/('opaque-'+str(defined)+'.cpp');define='#ifdef OPAQUE\n#undef OPAQUE\n#endif\n'+('#define OPAQUE 937' if defined else '')
        check='#if !defined(OPAQUE) || OPAQUE != 937\n#error OPAQUE_not_restored\n#endif' if defined else '#ifdef OPAQUE\n#error OPAQUE_leaked\n#endif'
        f.write_text(includes+'\n'+define+'\n#include <test/util/shielded_v2_egress_fixture.h>\n#include <test/util/shielded_v2_egress_fixture.h>\n'+check+'\n')
        cmd=row['command'];old_source=row['file'].replace('/', '\\');old_output=str(Path(row['output']).relative_to(BUILD)).replace('/', '\\');assert old_source in cmd and old_output in cmd;cmd=cmd.replace(old_source,str(f)).replace(old_output,str(f.with_suffix('.obj')))
        s.need('opaque-scope-'+str(defined),cmd,240,BUILD)
    text=(SOURCE/'src/test/matmul_backend_capabilities_tests.cpp').read_text();cases=text[text.index('BOOST_AUTO_TEST_CASE(scoped_environment_'):text.index('BOOST_AUTO_TEST_CASE(cpu_backend_always_available)')]
    f=E/'environment-controls.cpp';f.write_text('#define BOOST_TEST_MODULE environment_fixture_controls\n#include <boost/test/included/unit_test.hpp>\n#include <test/util/environment.h>\n#include <stdexcept>\nusing test::ScopedEnvVar;\n'+cases)
    inc=ROOT/'vcpkg-installed/x64-windows-static/include';assert(inc/'boost/test/included/unit_test.hpp').exists()
    for compiler in ['cl','clang-cl']:
        out=E/('environment-'+compiler+'.exe');cmd=[compiler,'/nologo','/std:c++20','/EHsc','/MT','/I'+str(SOURCE/'src'),'/I'+str(inc),str(f),'/Fe'+str(out),'/Fo'+str(E/('environment-'+compiler+'.obj'))]
        s.need('environment-build-'+compiler,cmd,240,BUILD);s.need('environment-run-'+compiler,[str(out),'--report_level=detailed','--log_level=test_suite'],60,BUILD);R.setdefault('environment_binaries',{})[compiler]=sha(out);s.save()

def pair():
    assert R['status']=='PAIRS_READY';rows=rows_for(I['env_targets']+I['opaque_targets']);(E/'fixture-generated-commands.json').write_text(json.dumps(dict(rows),indent=2)+'\n')
    baseline_file=P/'baseline/baseline-evidence.json';assert sha(baseline_file)==I['reused_baseline_sha256'];b=json.loads(baseline_file.read_text())
    assert b['cached_source']==BASE and b['generated_inputs']==R['generated_inputs_before_pair']
    assert b['source_catalog_canonical_sha256']==hashlib.sha256(json.dumps(R['source_catalog'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    # Commands, compiler/SDK, source and every generated input match the saved
    # actual baseline. A Ninja/image packaging change cannot alter these direct
    # compiler invocations; all other profile differences are refused.
    pd=differences(b['actual_profile'],R['actual_profile']);allowed=json.loads((P/'profile-transition.json').read_text())['allowed_differences'];assert not pd or pd==allowed
    before=b['rows'];assert {n:r for n,r in rows}=={r['file']:r['command']for r in before}
    for r in before:
        f=P/'baseline'/r['log'];assert sha(f)==r['log_sha256'];shutil.copyfile(f,E/r['log'])
    R['fixture-before']=before;R['reused_baseline']={'run':b['run'],'controls':b['controls'],'artifact':b['artifact'],'reason':b['reason'],'manifest_sha256':I['reused_baseline_sha256'],'new_baseline_compiler_commands':0};s.save()
    known=set(I['known_env_targets']+I['opaque_targets'])
    assert all(r['exit']==0 or (r['env_diagnostics'] if r['file'] in I['known_env_targets'] else r['opaque_diagnostics']) for r in before if r['file']in known),[(r['file'],r['exit'],r['env_diagnostics'],r['opaque_diagnostics'])for r in before if r['file']in known]
    R['extra_baseline_prerequisites']=[r for r in before if r['file']not in known and r['exit']!=0 and not r['env_diagnostics']];s.save()
    assert next(r for r in before if r['file']=='matmul_matrix_tests.cpp')['env_diagnostics']
    assert any(r['exit']!=0 and r['opaque_diagnostics'] for r in before if r['file']in I['opaque_targets'])
    R['already_passing_baseline_controls']=[r['file']for r in before if r['exit']==0];s.save()
    assert metadata()==R['generated_inputs_before_pair'];patch=P/'fixtures.patch';assert sha(patch)==I['patch_sha256']
    s.need('fixture-apply-check',['git','apply','--check',str(patch)],30);s.need('fixture-apply',['git','apply','--index',str(patch)],30)
    tree=subprocess.check_output(['git','write-tree'],cwd=SOURCE,text=True).strip();assert tree==I['integration_tree'];env=os.environ.copy();env.update(I['commit_environment'])
    commit=subprocess.check_output(['git','commit-tree',tree,'-p',BASE],input=I['integration_message'],cwd=SOURCE,text=True,env=env).strip();assert commit==TARGET
    s.need('fixture-clean-integration',['git','reset','--hard',TARGET],30);R['source_catalog']=s.catalog(TARGET,'fixture-before')
    delta=subprocess.check_output(['git','diff','--name-only',BASE,TARGET],cwd=SOURCE,text=True).splitlines();assert delta==I['changed_paths'];R['source_delta']=delta;R['status']='CANDIDATE_PAIR';s.save()
    after=batch('fixture-after',rows+rows_for(['matmul_backend_capabilities_tests.cpp']));assert all(r['exit']==0 for r in after if r['file']in known or r['file']=='matmul_backend_capabilities_tests.cpp'),[(r['file'],r['exit'])for r in after if r['file']in known];assert metadata()==R['generated_inputs_before_pair']
    controls();R['same_generated_commands_before_after']=True;R['known_fixture_pairs_pass']=True;R['remaining_prerequisites']=[r for r in after if r['exit']!=0];R['status']='KNOWN_FIXTURES_PASS_EXTRA_PREREQUISITES'if R['remaining_prerequisites']else'KNOWN_FIXTURES_PASS';s.save()
    if R['remaining_prerequisites']:raise RuntimeError('Scoped known fixtures pass; additional generated-object prerequisites block broad unit resumption')

def unitbuild():
    assert R['status']=='KNOWN_FIXTURES_PASS' and s.catalog(TARGET,'fixture-pre-units')==R['source_catalog'];common=['ninja','-C',str(BUILD),'-f',str(E/'fixture-resume.ninja')]
    s.need('fixture-unit-plan',common+['-d','explain','-n','test_btx'],120);txt=(E/'fixture-unit-plan.log').read_text(errors='replace');assert 'command line changed for' not in txt
    R['status']='UNITS_BUILDING';s.save();code=s.run('candidate-unit-build',common+['--verbose','-j','4','-k','1','test_btx'],6600);R['unit_build_exit']=code
    if code:R['status']='UNIT_BUILD_FAILURE';raise RuntimeError('Next actual compiler/link blocker; original log retained')
    unit=BUILD/'bin/test_btx.exe';R['unit_binary_sha256']=sha(unit);R['unit_built']=True;s.need('fixture-unit-inventory',[str(unit),'--list_content'],60);R['status']='UNITS_BUILT';s.save()

def unitrun():
    assert R['status']=='UNITS_BUILT';unit=BUILD/'bin/test_btx.exe';assert sha(unit)==R['unit_binary_sha256'];data=Path('D:/bf'+os.environ['GITHUB_RUN_ID']);assert not data.exists();data.mkdir();R['unit_data']=str(data);R['unit_invoked']=True;s.save()
    code=s.run('candidate-unit-run',[str(unit),'--log_level=error','--report_level=detailed','--catch_system_errors=yes','--','-testdatadir='+str(data)],3600);R['unit_exit']=code;txt=(E/'candidate-unit-run.log').read_text(errors='replace');m=re.search(r'Running (\d+) test cases?',txt);R['unit_cases_started']=int(m.group(1))if m else 0
    assert sha(unit)==R['unit_binary_sha256'];s.quiesce();R['status']='UNITS_PASS'if code==0 and R['unit_cases_started']>0 else'UNIT_RUN_FAILURE';s.save()
    if R['status']!='UNITS_PASS':raise RuntimeError('Maintained units failed')

def retain():
    assert not R['process_active'] and R.get('cleanup_confirmed',True);assert R.get('source_catalog',{}).get('head')==TARGET,'No coherent candidate to retain'
    s.quiesce();current=s.catalog(TARGET,'fixture-retained');assert current==R['source_catalog'];R['profile']={'source':TARGET,'cached_input_profile':R['cached_profile'],'actual_current_profile':R['actual_profile'],'explicit_host_transition':R['host_transition'],'configuration_hashes':I['configuration_hashes'],'fixture_script_sha256':sha(P/'fixtures.py'),'patch_sha256':I['patch_sha256'],'kind':'test-only delta on PR411; frozen configuration; real version-header updates allowed'}
    R['checkpoint_capture']=checkpoint.capture(ROOT,SOURCE,R['profile'],current,{'status':R['status'],'unit_build_exit':R.get('unit_build_exit'),'unit_exit':R.get('unit_exit')});shutil.copyfile(BUILD/'btx-checkpoint.json',E/'fixture-checkpoint.json');cp=json.loads((BUILD/'btx-checkpoint.json').read_text());R['objects_retained']=sum(k.endswith('.obj')for k in cp['files']);key=hashlib.sha256(json.dumps(R['profile'],sort_keys=True).encode()).hexdigest();R['checkpoint_key']=key;s.save()
    with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8')as f:f.write('checkpoint_valid=true\ncheckpoint_key='+key+'\n')

stage=sys.argv[1];failed=False
try:{'prepare':prepare,'pair':pair,'unitbuild':unitbuild,'unitrun':unitrun,'retain':retain}[stage]()
except BaseException as ex:failed=True;R.setdefault('failures',[]).append({'stage':stage,'type':type(ex).__name__,'error':str(ex)});print(type(ex).__name__,str(ex),flush=True)
finally:s.save();print(json.dumps({k:R.get(k)for k in ['status','unit_built','unit_invoked','objects_retained','failures']},indent=2),flush=True)
raise SystemExit(1 if failed else 0)
