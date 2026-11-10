"""Build the exact #503 helper from an isolated verified Linux checkpoint."""
from pathlib import Path
import json, os, re, shutil, signal, subprocess, tarfile, time
from checkpoint import sha, restore_timestamps, verify_restored

BASE = 'dac9aee53520bd49ed320ec7a49b9072fc7d88d9'
ARCHIVE = '90391b49487f57e3c820200f28142e6873b0fecbb2a2d4b82091e48050437176'
AUTHOR = '08fd0a6245598e8f9fedc6dac97629310335dd2d'
TREE = '1fa445dd7b06901baf7888b97e6dbf79ac02ef0e'
FILES = {
 'src/modelnet/catalog.cpp':'a2452cb500b954b40e51e9f1ae377c45918f1a3d',
 'src/modelnet/feed.cpp':'0a27b99b90df7ffcb856a1a463cb71f0c5d76020',
 'src/modelnet/helper.cpp':'c8a6746a2ee4bbbc1e12e11d8f78a87209d08a5b',
 'src/modelnet/search.cpp':'172f39b5cb06d3708aa75b18dff5f8d217ffe313',
 'src/test/CMakeLists.txt':'76bc81446a18a6ef7db5cf6396ddf081d7e1e008',
 'src/test/modelnet_store_write_tests.cpp':'481704aa7004cf67025cb4379eb7d95395d319b0',
}
STOCK = '0412b4d3d09ecd40e954f031ba4d2487e089a078084669af9ec598b041ba1a6c'

def main():
    w = Path(os.environ['GITHUB_WORKSPACE']).resolve()
    recipe = Path(__file__).resolve().parent
    out = w / 'build-records'; out.mkdir(exist_ok=True)
    binaries = w / 'helper-binaries'; binaries.mkdir(exist_ok=True)
    result = {'compiled': False, 'commands': [], 'base': BASE, 'candidate_commit': AUTHOR}
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
        assert run(['git','rev-parse','HEAD'],'author-head',accepted).strip() == AUTHOR
        assert run(['git','rev-parse','HEAD^{tree}'],'author-tree',accepted).strip() == TREE
        assert not run(['git','status','--porcelain','--untracked-files=all'],'author-clean',accepted).strip()
        observed = set(run(['git','diff','--name-only',BASE,AUTHOR],'author-delta',accepted).splitlines())
        assert observed == set(FILES), observed
        # Full checkpoint verification above includes generated/untracked files.
        # Copy only the exact six author files; preserve every other timestamp.
        for name, blob in FILES.items():
            assert run(['git','hash-object',name],name.replace('/','_')+'-blob',accepted).strip() == blob
            (src/name).parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(accepted/name,src/name)
            (src/name).touch()
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
        # Head/index metadata is the author's exact tree; untracked caches are
        # recorded separately rather than pretending the restored tree is empty.
        assert run(['git','rev-parse','HEAD'],'candidate-head',src).strip()==AUTHOR
        assert run(['git','write-tree'],'candidate-tree',src).strip()==TREE
        assert not run(['git','status','--porcelain','--untracked-files=no'],'candidate-clean',src).strip()
        result['candidate_tree']=TREE
        assert run(['g++','-dumpfullversion'],'compiler').strip() == '11.4.0'
        assert 'OpenSSL 3.5.9' in run([w/'gui-pilot-runtime/openssl/bin/openssl','version'],'openssl')
        stock = w/'stock-input/base'; assert sha(stock) == STOCK
        prior = json.loads((w/'stock-build-input/result.json').read_text())
        assert prior['pass'] and prior['archive_unchanged'] and prior['binaries']['base'] == STOCK
        shutil.copy2(stock,binaries/'base'); (binaries/'base').chmod(0o755)
        run(['cmake','-S',src,'-B',build],'candidate-configure',timeout=240)
        cache = (build/'CMakeCache.txt').read_text()
        assert 'WITH_MODELNET:BOOL=ON' in cache and str(w/'gui-pilot-runtime/openssl/lib/libcrypto.a') in cache
        run(['cmake','-P',build/'CMakeFiles/VerifyGlobs.cmake'],'candidate-globs',build)
        manifest = out/'candidate.ninja'; shutil.copy2(build/'build.ninja',manifest)
        dry = run(['ninja','-C',build,'-f',manifest,'-d','explain','-n','btx-modeld'],'candidate-plan')
        assert 'Re-running CMake' not in dry and 'Re-checking globbed' not in dry
        actions = [re.sub(r'^\[\d+/\d+\] ','',line) for line in dry.splitlines() if re.match(r'^\[\d+/\d+\] ',line)]
        allowed = {
            'Generating bitcoin-build-info.h',
            'Building CXX object src/CMakeFiles/bitcoin_clientversion.dir/clientversion.cpp.o',
            'Building CXX object src/CMakeFiles/bitcoin_common.dir/matmul/matmul_v4_rc_production_canary.cpp.o',
            'Building CXX object src/CMakeFiles/bitcoin_common.dir/matmul/matmul_v4_rc_production_golden_manifest.cpp.o',
            'Building CXX object src/modelnet/CMakeFiles/btx-modeld.dir/__/modeld.cpp.o',
            'Building CXX object src/modelnet/CMakeFiles/bitcoin_modelnet.dir/catalog.cpp.o',
            'Building CXX object src/modelnet/CMakeFiles/bitcoin_modelnet.dir/helper.cpp.o',
            'Building CXX object src/modelnet/CMakeFiles/bitcoin_modelnet.dir/feed.cpp.o',
            'Building CXX object src/modelnet/CMakeFiles/bitcoin_modelnet.dir/search.cpp.o',
            'Linking CXX static library lib/libbitcoin_clientversion.a',
            'Linking CXX static library lib/libbitcoin_common.a',
            'Linking CXX static library lib/libbitcoin_modelnet.a',
            'Linking CXX executable bin/btx-modeld',
        }
        result['actions'] = actions
        assert 0 < len(actions) <= 13 and len(actions)==len(set(actions)) and set(actions) <= allowed, actions
        assert all(any(f'/{unit}.cpp.o' in a for a in actions) for unit in ('catalog','helper','feed','search'))
        assert 'Linking CXX executable bin/btx-modeld' in actions
        run(['ninja','-C',build,'-t','commands','btx-modeld'],'candidate-commands')
        result['compile_started'] = True
        run(['ninja','-C',build,'-f',manifest,'-j1','btx-modeld'],'candidate-compile',timeout=1200)
        result['compiled'] = True
        shutil.copy2(build/'bin/btx-modeld',binaries/'candidate')
        result['binaries'] = {name: sha(binaries/name) for name in ('base','candidate')}
        assert result['binaries']['base'] != result['binaries']['candidate']
        for name in ('base','candidate'):
            assert 'not found' not in run(['ldd',binaries/name],name+'-ldd')
        assert sha(archive) == ARCHIVE
        result.update(original_checkpoint_unchanged=True, stock_binary_reused=True, passed=True)
    except Exception as error:
        result.update(passed=False,error=repr(error))
    finally:
        (out/'build-result.json').write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['passed'] else 1

if __name__ == '__main__': raise SystemExit(main())
