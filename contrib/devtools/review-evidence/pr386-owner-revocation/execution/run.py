#!/usr/bin/env python3
"""Recorded workspace partial relink, isolated source/objects; not a clean build."""
from pathlib import Path
import hashlib,json,os,platform,shutil,subprocess,time
OUT=Path(__file__).resolve().parent
TOOLS=OUT.parents[1]
REPO=TOOLS/'toolchain-2026-10-31/source'
PRIOR=TOOLS/'channel-freeze-recovery/execution'
SOURCE=OUT/'source'
BUILD=OUT/'build'
RESULTS=OUT/'results'
TARGET='b1be792041f9337b4d8e1156f8b6aa76b8e09277'
BASE='fd3a905fed3bc4943ad24372da032af4d29304a3'
FLOOR=1342177280
LIMIT=12*1024*1024
NAME='owner-revoked-active-freezes-once-and-unrelated-permit-survives-reopen'
manifest={'target':TARGET,'base':BASE,'profile':'native macOS arm64 synchronous component partial relink','platform':platform.platform(),'commands':[],'source_inputs':[],'readonly_inputs':[],'minimum_free_bytes':2**63,'peak_owned_bytes':0}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def measure():
    free=shutil.disk_usage(OUT).free
    owned=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
    manifest['minimum_free_bytes']=min(free,manifest['minimum_free_bytes'])
    manifest['peak_owned_bytes']=max(owned,manifest['peak_owned_bytes'])
    if free<FLOOR or owned>LIMIT:raise RuntimeError(f'resource bound: free={free}, owned={owned}')
def command(args,label,expected=0):
    measure();start=time.monotonic()
    with (OUT/(label+'.log')).open('w') as log:
        proc=subprocess.Popen([str(x) for x in args],stdout=log,stderr=subprocess.STDOUT)
        try:
            while proc.poll() is None:measure();time.sleep(.1)
        except BaseException:
            proc.terminate();proc.wait(timeout=10);raise
        code=proc.returncode
    manifest['commands'].append({'argv':[str(x) for x in args],'returncode':code,'elapsed_seconds':time.monotonic()-start,'log':label+'.log'})
    measure()
    if code!=expected:raise RuntimeError(f'{label}: unexpected exit {code}, expected {expected}; preserve log')
    return code
if BUILD.exists() or RESULTS.exists():raise SystemExit('Preserve existing execution; do not overwrite or repeat automatically')
BUILD.mkdir();RESULTS.mkdir(mode=0o700)
prior=json.loads((PRIOR/'native-integration.json').read_text())
try:
    measure()
    for row in prior['compiled_repository_inputs']:
        rel=row['target_path'];data=subprocess.check_output(['git','-C',str(REPO),'show',TARGET+':'+rel])
        assert hashlib.sha256(data).hexdigest()==row['sha256'],rel
        if rel=='test/util/model_security/channel_recovery_tests.cpp':
            manifest['source_inputs'].append({'path':rel,'sha256':sha(SOURCE/rel),'git_revision':'test-only candidate.patch on '+TARGET})
            continue
        dest=SOURCE/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        manifest['source_inputs'].append({'path':rel,'sha256':sha(dest),'git_revision':TARGET})
    for row in prior['fresh_archives']:
        path=PRIOR/row['path'];assert sha(path)==row['sha256'],path
        manifest['readonly_inputs'].append({'path':str(path),'sha256':sha(path),'provenance_manifest':str(PRIOR/'native-integration.json')})
    sqlite=Path(prior['sqlite']['library']);assert sha(sqlite)==prior['sqlite']['sha256']
    assert sha('/opt/homebrew/opt/sqlite/include/sqlite3.h')==prior['sqlite']['header_sha256']
    manifest['readonly_inputs'].append({'path':str(sqlite),'sha256':sha(sqlite)})
    harness=SOURCE/'test/util/model_security/channel_recovery_tests.cpp'
    manifest['harness_sha256']=sha(harness)
    lifecycle=SOURCE/'src/modelnet/security_v2/lifecycle.cpp'
    exact='                    if(!rollback&&row[4]=="frozen"&&row[3].empty()&&acknowledged)continue;\n'
    text=lifecycle.read_text();assert text.count(exact)==1
    knownbad=BUILD/'lifecycle.continue-removed.cpp';knownbad.write_text(text.replace(exact,''))
    manifest['known_bad']={'change':'remove acknowledged owner-revoked frozen/no-candidate continuation only','target_lifecycle_sha256':sha(lifecycle),'known_bad_lifecycle_sha256':sha(knownbad)}
    flags=['/usr/bin/c++','-O3','-DNDEBUG','-std=gnu++20','-arch','arm64','-isysroot','/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk']
    inc=['-I'+str(SOURCE/'src'),'-I'+str(SOURCE/'src/libbitcoinpqc/include'),'-I'+str(SOURCE/'src/libbitcoinpqc/dilithium/ref'),'-I'+str(SOURCE/'src/univalue/include'),'-isystem','/opt/homebrew/opt/sqlite/include']
    command(flags+inc+['-o',BUILD/'harness.o','-c',harness],'compile-harness')
    command(flags+inc+['-Wall','-Wextra','-Wpedantic','-Werror','-o',BUILD/'lifecycle.knownbad.o','-c',knownbad],'compile-knownbad')
    libs=[PRIOR/'native-build'/x for x in ['libbtx_model_security.a','libbtx_security_crypto.a','libbtx_security_json.a']]+[sqlite]
    for variant,extra in [('target',[]),('knownbad',[BUILD/'lifecycle.knownbad.o'])]:
        binary=BUILD/('channel-'+variant)
        command(flags+[BUILD/'harness.o']+extra+['-o',binary]+libs,'link-'+variant)
        manifest.setdefault('binaries',{})[variant]={'sha256':sha(binary)}
        summary=RESULTS/(variant+'.json')
        command([binary,summary,NAME],'run-'+variant,expected=0 if variant=='target' else 1)
        result=json.loads(summary.read_text());assert len(result['tests'])==1 and result['tests'][0]['name']==NAME
        if variant=='target':assert result['passed']==1 and result['failed']==0
        else:assert result['failed']==1 and result['tests'][0]['error']=='repeated owner-revoked Tick revoked unrelated new permit'
        manifest['binaries'][variant]['result']=result
    summary=RESULTS/'quarantine-target.json'
    command([BUILD/'channel-target',summary,'recovery-still-checks-owner-candidate-and-canary'],'run-quarantine-target')
    manifest['quarantine_result']=json.loads(summary.read_text());assert manifest['quarantine_result']['passed']==1
    phase_bad=BUILD/'lifecycle.phase-disjunct-removed.cpp'
    exact_phase='row[1].empty()||active_invalid?"frozen":"active"'
    assert text.count(exact_phase)==1
    phase_bad.write_text(text.replace(exact_phase,'row[1].empty()?"frozen":"active"'))
    command(flags+inc+['-Wall','-Wextra','-Wpedantic','-Werror','-o',BUILD/'lifecycle.phasebad.o','-c',phase_bad],'compile-phasebad')
    command(flags+[BUILD/'harness.o',BUILD/'lifecycle.phasebad.o','-o',BUILD/'channel-phasebad']+libs,'link-phasebad')
    summary=RESULTS/'quarantine-knownbad.json'
    command([BUILD/'channel-phasebad',summary,'recovery-still-checks-owner-candidate-and-canary'],'run-quarantine-knownbad',expected=1)
    phase_result=json.loads(summary.read_text())
    assert phase_result['failed']==1 and phase_result['tests'][0]['error']=='invalid active appeared recovered after candidate quarantine'
    manifest['quarantine_knownbad']={'source_sha256':sha(phase_bad),'object_sha256':sha(BUILD/'lifecycle.phasebad.o'),'binary_sha256':sha(BUILD/'channel-phasebad'),'result':phase_result}
    manifest['outcome']='PASS target new regression; intended known-bad failure; existing quarantine control PASS'
finally:
    manifest['temporary_fixture_directories_remaining']=[str(x) for x in Path('/private/tmp').glob('btx-security-test-*')]
    manifest['harness_object_sha256']=sha(BUILD/'harness.o') if (BUILD/'harness.o').exists() else None
    (OUT/'execution-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
