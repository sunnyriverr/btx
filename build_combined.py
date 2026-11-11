"""Build only btxd for a pinned single-file wallet restore repair from an isolated verified Linux checkpoint."""
from pathlib import Path
import json, os, re, shutil, signal, subprocess, tarfile, time, traceback
from checkpoint import sha, restore_timestamps, verify_restored, create

BASE = 'dac9aee53520bd49ed320ec7a49b9072fc7d88d9'
ARCHIVE = '90391b49487f57e3c820200f28142e6873b0fecbb2a2d4b82091e48050437176'
DAEMON = 'ffd6c2dc95df0111a8152b5d5f82244190cad2323981376ffed7c21a1cfd9fc6'
TARGETS = {'src/wallet/wallet.cpp', 'src/wallet/rpc/labels.cpp', 'src/wallet/sqlite.cpp'}

def main():
    w = Path(os.environ['GITHUB_WORKSPACE']).resolve()
    recipe = Path(__file__).resolve().parent
    out = w / 'build-records'; out.mkdir(exist_ok=True)
    binaries = w / 'daemon-binaries'; binaries.mkdir(exist_ok=True)
    result = {'compiled': False, 'commands': [], 'base': BASE, 'product_delta': sorted(TARGETS)}
    def run(args, name, cwd=None, timeout=180):
        started = time.monotonic()
        print(name, flush=True)
        logpath = out / (name + '.log')
        with logpath.open('wb') as log, logpath.open('rb') as live:
            proc = subprocess.Popen(list(map(str, args)), cwd=cwd, stdout=log,
                                    stderr=subprocess.STDOUT, start_new_session=True)
            while proc.poll() is None:
                fresh = live.read()
                if fresh: print(fresh.decode(errors='replace'),end='',flush=True)
                if time.monotonic() - started > timeout or shutil.disk_usage(w).free < 2*1024**3:
                    os.killpg(proc.pid, signal.SIGTERM)
                    try: proc.wait(10)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL); proc.wait()
                    raise RuntimeError(name + ' exceeded time/disk bound')
                time.sleep(.25)
            fresh = live.read()
            if fresh: print(fresh.decode(errors='replace'),end='',flush=True)
        result['commands'].append({'label': name, 'exit': proc.returncode,
                                   'seconds': time.monotonic() - started})
        assert proc.returncode == 0, name
        return (out / (name + '.log')).read_text(errors='replace')
    try:
        assert shutil.disk_usage(w).free > 10*1024**3
        saved = w / 'saved-checkpoint'; archive = saved / 'build-state.tar.gz'
        m = json.loads((saved / 'manifest.json').read_text())
        assert sha(archive) == ARCHIVE == m['archive_sha256']
        assert m['identity']['source'] == BASE and Path(m['workspace']) == w
        assert not (w/'product').exists() and not (w/'gui-pilot-runtime').exists()
        with tarfile.open(archive) as tar: tar.extractall(w, filter='data')
        restore_timestamps(w, m); verify_restored(w, m)
        result.update(restore_verified=True, checkpoint_sha256=ARCHIVE,
                      checkpoint_files=len(m['rows']))
        src = w/'product'; build = w/'gui-pilot-runtime/qtbuild'
        accepted = w/'accepted-source'
        assert run(['git','rev-parse','HEAD'],'accepted-head',accepted).strip() == BASE
        assert not run(['git','status','--porcelain','--untracked-files=all'],'accepted-clean',accepted).strip()
        shutil.copytree(accepted/'.git', src/'.git')
        names = run(['git','ls-files'],'tracked-files',accepted).splitlines()
        source_manifest = {}
        for name in names:
            target, expected = src/name, accepted/name
            if expected.is_symlink():
                assert target.is_symlink() and os.readlink(target)==os.readlink(expected),name
                source_manifest[name] = {'kind':'link','target':os.readlink(target)}
            else:
                assert expected.is_file() and target.is_file() and not target.is_symlink(),name
                assert sha(target)==sha(expected),name
                assert (target.stat().st_mode & 0o111)==(expected.stat().st_mode & 0o111),name
                source_manifest[name] = {'kind':'file','sha256':sha(target)}
        (out/'tracked-source.json').write_text(json.dumps(source_manifest,indent=2,sort_keys=True)+'\n')
        extras = {}
        for p in src.rglob('*'):
            rel = p.relative_to(src)
            if '.git' in rel.parts or str(rel) in source_manifest: continue
            if p.is_symlink(): extras[str(rel)]={'kind':'link','target':os.readlink(p)}
            elif p.is_file(): extras[str(rel)]={'kind':'file','sha256':sha(p)}
        (out/'retained-untracked.json').write_text(json.dumps(extras,indent=2,sort_keys=True)+'\n')
        result['retained_untracked_count']=len(extras)
        assert not run(['git','status','--porcelain','--untracked-files=no'],'base-clean',src).strip()
        spec = json.loads((recipe/'combined/manifest.json').read_text())
        assert spec['base']==BASE and set(spec['files'])==TARGETS
        result['repair_sha256'] = {}
        for target in sorted(TARGETS):
            repair = recipe/'combined'/Path(target).name
            assert repair.is_file() and not repair.is_symlink()
            assert sha(repair) == spec['files'][target] and sha(repair) != sha(src/target)
            result['repair_sha256'][target] = sha(repair)
            shutil.copyfile(repair, src/target)
            (src/target).touch()
        assert set(run(['git','diff','--name-only'],'changed-files',src).splitlines())==TARGETS
        run(['git','diff','--check'],'repair-whitespace',src)
        run(['git','diff','--binary'],'repair-patch',src)
        run(['git','add',*sorted(TARGETS)],'repair-index',src)
        result['candidate_tree']=run(['git','write-tree'],'repair-tree',src).strip()
        assert not run(['git','diff','--name-only'],'unstaged-files',src).strip()
        assert set(run(['git','diff','--cached','--name-only'],'staged-files',src).splitlines())==TARGETS
        (out/'repair-input.json').write_text(json.dumps(spec,indent=2)+'\n')
        assert run(['g++','-dumpfullversion'],'compiler').strip() == '11.4.0'
        assert 'OpenSSL 3.5.9' in run([w/'gui-pilot-runtime/openssl/bin/openssl','version'],'openssl')
        initial_binaries={n:sha(build/'bin'/n) for n in ('btxd','btx-cli','btx-qt') if (build/'bin'/n).exists()}
        assert initial_binaries == {'btx-qt':'7239c3b1e80e8114e47ebf3bd5b060b95c23db746dd70533681a9858763329a5'}
        stock=w/'saved-daemon/btxd'
        assert sha(stock)==DAEMON
        result['original_binaries']=initial_binaries
        result['stock_daemon_run']=42918244124
        shutil.copy2(stock,binaries/'base')
        (binaries/'base').chmod(0o755)
        shutil.copy2(build/'CMakeCache.txt',out/'cache-before.txt')
        def profile(text):
            rows={}
            for line in text.splitlines():
                if line.startswith(('#','//')) or ':' not in line or '=' not in line: continue
                key,tail=line.split(':',1); kind,value=tail.split('=',1)
                if kind=='BOOL' or key in ('CMAKE_BUILD_TYPE','CMAKE_CXX_COMPILER','CMAKE_C_COMPILER','CMAKE_CXX_FLAGS','CMAKE_C_FLAGS','CMAKE_CXX_FLAGS_RELEASE','CMAKE_C_FLAGS_RELEASE','CMAKE_EXE_LINKER_FLAGS','CMAKE_STATIC_LINKER_FLAGS','OPENSSL_CRYPTO_LIBRARY','OPENSSL_SSL_LIBRARY'):
                    rows[key]=[kind,value]
            return rows
        original_profile=profile((build/'CMakeCache.txt').read_text())
        result['checkpoint_verifier_sha256']=sha(recipe/'checkpoint.py')
        result['repair_patch_sha256']=sha(out/'repair-patch.log')
        for target in TARGETS:
            source_manifest[target]={'kind':'file','sha256':sha(src/target)}
        (out/'candidate-source.json').write_text(json.dumps(source_manifest,indent=2,sort_keys=True)+'\n')
        run(['cmake','-S',src,'-B',build,'-DBUILD_DAEMON=ON'],'candidate-configure',timeout=240)
        cache = (build/'CMakeCache.txt').read_text()
        assert all(flag in cache for flag in ('BUILD_DAEMON:BOOL=ON','ENABLE_WALLET:BOOL=ON','WITH_SQLITE:BOOL=ON'))
        assert str(w/'gui-pilot-runtime/openssl/lib/libcrypto.a') in cache
        shutil.copy2(build/'CMakeCache.txt',out/'cache-after.txt')
        result['build_profile']=profile(cache)
        expected_profile=dict(original_profile)
        assert expected_profile['BUILD_DAEMON']==['BOOL','OFF']
        expected_profile['BUILD_DAEMON']=['BOOL','ON']
        result['intentional_profile_delta']={'BUILD_DAEMON':['OFF','ON']}
        assert result['build_profile']==expected_profile, 'Unexpected configuration/compiler/OpenSSL profile change'
        run(['cmake','-P',build/'CMakeFiles/VerifyGlobs.cmake'],'candidate-globs',build)
        manifest = out/'candidate.ninja'; shutil.copy2(build/'build.ninja',manifest)
        dry = run(['ninja','-C',build,'-f',manifest,'-d','explain','-n','btxd'],'candidate-plan')
        assert 'Re-running CMake' not in dry and 'Re-checking globbed' not in dry
        actions = [re.sub(r'^\[\d+/\d+\] ','',line) for line in dry.splitlines() if re.match(r'^\[\d+/\d+\] ',line)]
        allowed = {
            'Generating bitcoin-build-info.h',
            'Building CXX object src/wallet/CMakeFiles/bitcoin_wallet.dir/wallet.cpp.o',
            'Building CXX object src/wallet/CMakeFiles/bitcoin_wallet.dir/rpc/labels.cpp.o',
            'Building CXX object src/wallet/CMakeFiles/bitcoin_wallet.dir/sqlite.cpp.o',
            'Building CXX object src/CMakeFiles/bitcoin_clientversion.dir/clientversion.cpp.o',
            'Building CXX object src/CMakeFiles/bitcoin_common.dir/matmul/matmul_v4_rc_production_canary.cpp.o',
            'Building CXX object src/CMakeFiles/bitcoin_common.dir/matmul/matmul_v4_rc_production_golden_manifest.cpp.o',
            'Building CXX object src/CMakeFiles/btxd.dir/bitcoind.cpp.o',
            'Building CXX object src/CMakeFiles/btxd.dir/init/bitcoind.cpp.o',
            'Linking CXX static library lib/libbitcoin_clientversion.a',
            'Linking CXX static library lib/libbitcoin_common.a',
            'Linking CXX static library lib/libbitcoin_wallet.a',
            'Linking CXX executable bin/btxd',
        }
        result['actions'] = actions
        assert 0 < len(actions) <= 13 and len(actions)==len(set(actions)) and set(actions) <= allowed, actions
        assert 'Building CXX object src/wallet/CMakeFiles/bitcoin_wallet.dir/wallet.cpp.o' in actions
        assert 'Linking CXX executable bin/btxd' in actions
        run(['ninja','-C',build,'-t','commands','btxd'],'candidate-commands')
        result['compile_started'] = True
        run(['ninja','-C',build,'-f',manifest,'-j1','btxd'],'candidate-compile',timeout=1200)
        result['compiled'] = True
        shutil.copy2(build/'bin/btxd',binaries/'candidate')
        result['binaries'] = {name: sha(binaries/name) for name in ('base','candidate')}
        assert all(sha(build/'bin'/n)==digest for n,digest in initial_binaries.items())
        assert result['binaries']['base'] != result['binaries']['candidate']
        for name in ('base','candidate'):
            assert 'not found' not in run(['ldd',binaries/name],name+'-ldd')
        assert sha(archive) == ARCHIVE
        result.update(original_checkpoint_unchanged=True, stock_binary_reused=True)
        # Preserve exact successor objects/source/profile for later qualification
        # or another bounded revision; checkpoint.py excludes private Git metadata.
        successor=create(w,w/'compiled-checkpoint',{
            'source':BASE,'repair_sha256':result['repair_sha256'],
            'candidate_tree':result['candidate_tree'],
            'candidate_daemon_sha256':result['binaries']['candidate']})
        result['successor_checkpoint_sha256']=successor['archive_sha256']
        result['passed']=True
    except Exception as error:
        result.update(passed=False,error=repr(error),traceback=traceback.format_exc())
    finally:
        (out/'build-result.json').write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['passed'] else 1

if __name__ == '__main__': raise SystemExit(main())
