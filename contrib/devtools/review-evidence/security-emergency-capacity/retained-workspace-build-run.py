#!/usr/bin/env python3
"""Exact-fd3a synchronous component partial relink; one explicit bounded run.
Requires retained readonly Mac component objects/libs at documented workspace paths.
No Service/worker/network; two short-lived harness threads exercise a last-slot race.
Baseline object cache is read-only; candidate uses the documented control allowance.
"""
from pathlib import Path
import hashlib,json,os,platform,re,shlex,subprocess,time
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
REV='fd3a905fed3bc4943ad24372da032af4d29304a3'
TREE=ROOT/'toolchain-2026-10-31/source'
HISTORICAL=ROOT/'pr275-runnable-queue/runtime/source'
COMMON=ROOT/'pr275-runnable-queue/runtime/build/CMakeFiles/security_common.dir/source/src/modelnet/security_v2'
DEPS=ROOT/'pr362-admission/build'
RESERVE=1.25*1024**3
MAXGROWTH=100*1024**2

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def gitbytes(path):return subprocess.check_output(['git','-C',str(TREE),'show',REV+':'+path])
def usage():return sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())
def free():s=os.statvfs(HERE);return s.f_bavail*s.f_frsize
record={'revision':REV,'platform':platform.platform(),'architecture':platform.machine(),'build_type':'partial relink of exact-baseline component objects; not clean build','commands':[],'run_count':0,'minimum_free_bytes':free(),'peak_owned_bytes':usage()}
def gate():
    avail=free();size=usage();record['minimum_free_bytes']=min(record['minimum_free_bytes'],avail);record['peak_owned_bytes']=max(record['peak_owned_bytes'],size)
    if avail<RESERVE or size>MAXGROWTH:raise RuntimeError('resource gate: free reserve or 100MiB owned size exceeded')
def command(args,log,expected=0):
    gate();args=list(map(str,args));record['commands'].append(args)
    with open(HERE/log,'w') as stream:
        proc=subprocess.Popen(args,stdout=stream,stderr=subprocess.STDOUT,env=dict(os.environ,TMPDIR=str(HERE/'tmp')))
        try:
            start=time.monotonic()
            while proc.poll() is None:
                gate()
                if time.monotonic()-start>90:raise RuntimeError('90-second command bound')
                time.sleep(.1)
        except BaseException:
            proc.terminate();proc.wait(timeout=5);raise
        gate()
        if proc.returncode!=expected:raise RuntimeError(f'command failed {proc.returncode}: {log}')

def main():
    gate();(HERE/'build').mkdir(exist_ok=True);(HERE/'tmp').mkdir(exist_ok=True,mode=0o700);(HERE/'results').mkdir(exist_ok=True,mode=0o700)
    inputs=[];headers={}
    objects=sorted(COMMON.glob('*.o'));assert len(objects)==11
    for obj in objects:
        source='src/modelnet/security_v2/'+obj.name[:-2]
        expected=gitbytes(source);assert expected==(HISTORICAL/source).read_bytes()==(ROOT/'store-quota-recovery/execution/source'/source).read_bytes(),source
        inputs.append({'path':str(obj.relative_to(ROOT)),'sha256':digest(obj),'source':source,'source_sha256':hashlib.sha256(expected).hexdigest(),'source_matches_revision':True})
        dependencies=shlex.split(obj.with_suffix(obj.suffix+'.d').read_text().replace('\\\n',' '))[1:]
        for dep in dependencies:
            p=Path(dep)
            for prefix in (HISTORICAL,TREE):
                if p.is_relative_to(prefix):
                    rel=str(p.relative_to(prefix));data=p.read_bytes();assert data==gitbytes(rel),rel;headers[rel]=hashlib.sha256(data).hexdigest();break
    record['reused_objects']=inputs;record['verified_repository_dependencies']=headers
    archives=[DEPS/'lib/libbitcoinpqc.a',DEPS/'lib/libbitcoin_crypto.a',DEPS/'src/univalue/libunivalue.a']
    prior=json.loads((ROOT/'channel-freeze-recovery/execution/baseline-build-run.json').read_text())
    expected_archives={x['path']:x['sha256'] for x in prior['archives']}
    for p in archives:assert digest(p)==expected_archives[str(p)],p
    record['reused_archives']=[{'path':str(p.relative_to(ROOT)),'sha256':digest(p)} for p in archives]
    record['candidate_sources']={str(x.relative_to(HERE/'source')):digest(x) for x in (HERE/'source').rglob('*') if x.is_file()}
    record['harness_sha256']=digest(HERE/'harness.cpp')
    flags=['-O2','-DNDEBUG','-std=c++20','-arch','arm64','-Wall','-Wextra','-Wpedantic','-Werror']
    includes=['-I'+str(HERE/'source/src'),'-I'+str(TREE/'src'),'-I'+str(TREE/'src/univalue/include'),'-I'+str(TREE/'src/libbitcoinpqc/include'),'-I/opt/homebrew/opt/sqlite/include']
    sqlite=Path('/opt/homebrew/opt/sqlite/lib/libsqlite3.dylib');record['sqlite']={'path':str(sqlite),'sha256':digest(sqlite),'header_sha256':digest(Path('/opt/homebrew/opt/sqlite/include/sqlite3.h'))}
    record['compiler']=subprocess.check_output(['/usr/bin/c++','--version'],text=True)
    command(['/usr/bin/c++',*flags,*includes,'-c',HERE/'harness.cpp','-o',HERE/'build/harness.o'],'compile.log')
    changed=[]
    for name in ('database.cpp','trust.cpp'):
        target=HERE/'build'/name.replace('.cpp','.o')
        command(['/usr/bin/c++',*flags,*includes,'-c',HERE/'source/src/modelnet/security_v2'/name,'-o',target],name+'.compile.log')
        changed.append(target)
    baseline=HERE/'build/baseline';candidate=HERE/'build/candidate'
    command(['/usr/bin/c++','-arch','arm64',HERE/'build/harness.o',*objects,*archives,sqlite,'-o',baseline],'baseline-link.log')
    candidate_objects=[x for x in objects if x.name not in ('database.cpp.o','trust.cpp.o')]+changed
    command(['/usr/bin/c++','-arch','arm64',HERE/'build/harness.o',*candidate_objects,*archives,sqlite,'-o',candidate],'candidate-link.log')
    record['binary_sha256']={'baseline':digest(baseline),'candidate':digest(candidate)}
    command([baseline,HERE/'results/baseline.json'],'baseline-run.log',expected=1)
    command([candidate,HERE/'results/candidate.json'],'candidate-run.log')
    before=json.loads((HERE/'results/baseline.json').read_text());after=json.loads((HERE/'results/candidate.json').read_text())
    assert [x['status'] for x in before['tests']]==['PASS','FAIL','FAIL','PASS'],before
    assert [x['status'] for x in after['tests']]==['PASS']*4,after
    assert [x['name'] for x in before['tests']]==[x['name'] for x in after['tests']]
    for key in ('late_write','late_policy_write'):
        assert before['observations'][key]['error']=='SEC_OBJECT_QUOTA'
        assert after['observations'][key]['error']=='SEC_DATABASE_WRITE'
    record['run_count']=2;record['checked_results']={'baseline':before,'candidate':after}
    assert not list((HERE/'tmp').iterdir()),'owned runtime fixture left over'
    (HERE/'tmp').rmdir();record['temporary_fixtures_remaining']=[];record['complete']=True
try:main()
finally:
    record['retained_owned_bytes']=usage();record['free_bytes_at_end']=free();(HERE/'build-run.json').write_text(json.dumps(record,indent=2)+'\n')
