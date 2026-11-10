"""Build the exact #495 helper from an isolated verified Linux checkpoint."""
from pathlib import Path
import json, os, re, shutil, signal, subprocess, tarfile, time
from checkpoint import sha, restore_timestamps, verify_restored

BASE = 'dac9aee53520bd49ed320ec7a49b9072fc7d88d9'
ARCHIVE = '90391b49487f57e3c820200f28142e6873b0fecbb2a2d4b82091e48050437176'
STOCK = '0412b4d3d09ecd40e954f031ba4d2487e089a078084669af9ec598b041ba1a6c'

def main():
    w = Path(os.environ['GITHUB_WORKSPACE']).resolve()
    recipe = Path(__file__).resolve().parent
    out = w / 'pr495-records'; out.mkdir(exist_ok=True)
    binaries = w / 'pr495-binaries'; binaries.mkdir(exist_ok=True)
    result = {'compiled': False, 'commands': [], 'base': BASE}
    def run(args, name, cwd=None, timeout=180):
        started = time.monotonic()
        with (out / (name + '.log')).open('wb') as log:
            proc = subprocess.Popen(list(map(str, args)), cwd=cwd, stdout=log,
                                    stderr=subprocess.STDOUT, start_new_session=True)
            while proc.poll() is None:
                if time.monotonic() - started > timeout or shutil.disk_usage(w).free < 2*1024**3:
                    os.killpg(proc.pid, signal.SIGTERM)
                    try: proc.wait(10)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL); proc.wait()
                    raise RuntimeError(name + ' exceeded time/disk bound')
                time.sleep(.25)
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
        shutil.copytree(w/'accepted-source/.git', src/'.git')
        assert run(['git','rev-parse','HEAD'], 'base-head',src).strip() == BASE
        assert not run(['git','status','--porcelain','--untracked-files=no'],'base-clean',src).strip()
        assert run(['g++','-dumpfullversion'],'compiler').strip() == '11.4.0'
        assert 'OpenSSL 3.5.9' in run([w/'gui-pilot-runtime/openssl/bin/openssl','version'],'openssl')
        stock = w/'stock-input/base'; assert sha(stock) == STOCK
        prior = json.loads((w/'stock-build-input/result.json').read_text())
        assert prior['pass'] and prior['archive_unchanged'] and prior['binaries']['base'] == STOCK
        shutil.copy2(stock,binaries/'base'); (binaries/'base').chmod(0o755)
        spec = json.loads((recipe/'source-manifest.json').read_text())
        for name, expected in spec['files'].items():
            source = recipe/'candidate'/name
            assert sha(source) == expected['sha256']
            shutil.copyfile(source, src/name)
            assert run(['git','hash-object',name],name.replace('/','_')+'-blob',src).strip() == expected['blob']
        assert set(run(['git','diff','--name-only'],'changed-files',src).splitlines()) == set(spec['files'])
        run(['git','add',*spec['files']],'candidate-index',src)
        tree = run(['git','write-tree'],'candidate-tree',src).strip()
        assert tree == spec['candidate_tree']; result['candidate_tree'] = tree
        result['candidate_commit'] = spec['candidate']
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
            'Linking CXX static library lib/libbitcoin_clientversion.a',
            'Linking CXX static library lib/libbitcoin_common.a',
            'Linking CXX static library lib/libbitcoin_modelnet.a',
            'Linking CXX executable bin/btx-modeld',
        }
        result['actions'] = actions
        assert 0 < len(actions) <= 12 and set(actions) <= allowed, actions
        assert any('catalog.cpp.o' in a for a in actions) and any('helper.cpp.o' in a for a in actions)
        assert 'Linking CXX executable bin/btx-modeld' in actions
        run(['ninja','-C',build,'-t','commands','btx-modeld'],'candidate-commands')
        result['compiled'] = True
        run(['cmake','--build',build,'--target','btx-modeld','--parallel','1'],'candidate-compile',timeout=1200)
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
