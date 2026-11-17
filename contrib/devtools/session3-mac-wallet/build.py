"""Manual-only hosted Mac build recipe. This file has not been executed."""
from pathlib import Path, PurePosixPath
import configparser, hashlib, json, os, platform, shutil, shlex, signal, subprocess, tarfile, time
import urllib.request, urllib.error, zipfile

W = Path(os.environ['GITHUB_WORKSPACE']).resolve()
P = Path(__file__).resolve().parent
M = json.loads((P / 'manifest.json').read_text())
S, B, R = W / 'product', W / 'mac-config-build', W / 'records'
R.mkdir(exist_ok=True)
RESERVE = 1342177280
STATE = {'complete': False, 'compiled': False, 'tests_run': False, 'source': M['source']}

def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()

def save():
    (R / 'result.json').write_text(json.dumps(STATE, indent=2) + '\n')

def live_bytes():
    return sum(p.stat().st_size for root in (S, B) if root.exists()
               for p in root.rglob('*') if p.is_file() and not p.is_symlink()
               and '.git' not in p.relative_to(W).parts)

def preservation_floor():
    # Keep room for a worst-case compressed checkpoint plus 3GiB margin,
    # and a further 512MiB while a command is being stopped.
    return max(RESERVE, live_bytes() + 3 * 1024**3 + 512 * 1024**2)

def cmd(args, name, seconds=120):
    assert shutil.disk_usage(W).free > preservation_floor(), 'Checkpoint headroom before ' + name
    with (R / (name + '.log')).open('wb') as log:
        proc = subprocess.Popen([str(a) for a in args], stdout=log,
                                stderr=subprocess.STDOUT, start_new_session=True)
        started = time.monotonic()
        try:
            while proc.poll() is None:
                if time.monotonic() - started > seconds or shutil.disk_usage(W).free < preservation_floor():
                    raise RuntimeError('Time/free-space bound: ' + name)
                time.sleep(1)
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait(timeout=10)
        assert proc.returncode == 0, (name, proc.returncode)
        assert shutil.disk_usage(W).free > preservation_floor(), 'Checkpoint headroom after ' + name
    return (R / (name + '.log')).read_text(errors='replace')

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None

def restore():
    # Token is sent only to api.github.com; artifact host receives no auth header.
    url = 'https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/' + str(M['artifact']) + '/zip'
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
                                              'User-Agent': 'BTX-Mac-preparation'})
    try:
        urllib.request.build_opener(NoRedirect).open(req, timeout=30)
        raise RuntimeError('Expected artifact redirect')
    except urllib.error.HTTPError as e:
        assert e.code == 302
        target = e.headers['Location']
    assert target.startswith('https://')
    outer = W / 'checkpoint.zip'
    with urllib.request.urlopen(target, timeout=60) as response, outer.open('wb') as out:
        copied = 0
        while True:
            chunk = response.read(1048576)
            if not chunk:
                break
            copied += len(chunk)
            assert copied <= M['outer_bytes']
            assert shutil.disk_usage(W).free > RESERVE
            out.write(chunk)
    assert copied == M['outer_bytes'] and sha(outer) == M['outer_sha256']
    inner = W / 'checkpoint.tar.gz'
    with zipfile.ZipFile(outer) as z:
        assert len(z.namelist()) == len(set(z.namelist()))
        invbytes = z.read('inventory.json')
        assert hashlib.sha256(invbytes).hexdigest() == M['inventory_sha256']
        inv = json.loads(invbytes)
        receipt = json.loads(z.read('receipt.json'))
        assert receipt['sha256'] == M['inner_sha256']
        with z.open('checkpoint.tar.gz') as src, inner.open('wb') as out:
            shutil.copyfileobj(src, out, 1048576)
    assert inner.stat().st_size == M['inner_bytes'] and sha(inner) == M['inner_sha256']
    seen = set()
    with tarfile.open(inner) as tar:
        for member in tar:
            path = PurePosixPath(member.name)
            assert not path.is_absolute() and '..' not in path.parts
            assert member.name not in seen
            seen.add(member.name)
            if not member.name.startswith('mac-config-build/'):
                continue
            meta = inv[member.name]
            dest = W / member.name
            assert dest.parent.resolve().is_relative_to(W)
            if member.isdir():
                assert meta['type'] == 'dir'
                dest.mkdir(parents=True, exist_ok=True)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            if member.issym():
                assert meta['type'] == 'symlink' and member.linkname == meta['target']
                assert (dest.parent / member.linkname).resolve().is_relative_to(W)
                dest.symlink_to(member.linkname)
                continue
            assert member.isfile() and meta['type'] == 'file'
            assert member.size == meta['bytes']
            with tar.extractfile(member) as src, dest.open('wb') as out:
                shutil.copyfileobj(src, out, 1048576)
            assert sha(dest) == meta['sha256']
            dest.chmod(meta['mode'])
            os.utime(dest, ns=(meta['mtime_ns'], meta['mtime_ns']))
            assert shutil.disk_usage(W).free > RESERVE
    selected = {n for n in inv if n.startswith('mac-config-build/')}
    assert selected <= seen, 'Incomplete retained build payload'
    cache = (B / 'CMakeCache.txt').read_text()
    assert 'CMAKE_HOME_DIRECTORY:INTERNAL=' + str(S) + '\n' in cache, 'Nonrelocatable cache: stop'
    # Preserve mtimes only for byte-identical current source; changed source stays dirty.
    matched = 0
    for name, meta in inv.items():
        dest = W / name
        if name.startswith('product/') and meta['type'] == 'file' and dest.is_file() and not dest.is_symlink():
            if sha(dest) == meta['sha256']:
                os.utime(dest, ns=(meta['mtime_ns'], meta['mtime_ns']))
                matched += 1
    STATE['matched_source_files'] = matched
    STATE['checkpoint_verified'] = True
    save()
    outer.unlink()
    inner.unlink()

def main():
    assert platform.system() == 'Darwin' and platform.machine() == 'arm64'
    assert shutil.disk_usage(W).free >= 15 * 1024**3, 'Independent runner capacity prerequisite'
    assert cmd(['git', '-C', S, 'rev-parse', 'HEAD'], 'head').strip() == M['source']
    assert not cmd(['git', '-C', S, 'status', '--porcelain'], 'initial-source-status').strip()
    assert 'Apple clang version 17.0.0' in cmd(['xcrun', 'clang++', '--version'], 'compiler')
    assert cmd(['xcrun', '--sdk', 'macosx', '--show-sdk-version'], 'sdk').strip() == '15.5'
    restore()
    # Use already-present dependencies only. Do not change a runner's packages implicitly.
    STATE['retained_openssl_hashes'] = M['openssl_static_sha256']
    # Establish actual links after configure; ModelNetOFF need not use OpenSSL.
    python = Path(cmd(['brew', '--prefix', 'python@3.12'], 'python-prefix').strip()) / 'bin/python3.12'
    assert python.is_file()
    assert cmd([python, '-c', 'import sys; print(sys.version_info[:2])'], 'python-version').strip() == '(3, 12)'
    # Fresh current checkout removes the old focused699 source overlay entirely.
    for name in ['src/test/CMakeLists.txt', 'src/test/main.cpp']:
        cmd(['git', '-C', S, 'diff', '--exit-code', '--', name], 'source-' + Path(name).name)
    args = ['cmake', '-S', S, '-B', B, '-DCMAKE_SUPPRESS_REGENERATION=ON',
            '-DCMAKE_BUILD_TYPE=Release', '-DENABLE_WALLET=ON', '-DWITH_SQLITE=ON', '-DBUILD_DAEMON=ON',
            '-DBUILD_CLI=ON', '-DBUILD_GUI=OFF', '-DBUILD_GUI_TESTS=OFF',
            '-DBUILD_TESTS=OFF', '-DBUILD_BENCH=OFF', '-DBUILD_FUZZ_BINARY=OFF',
            '-DWITH_MODELNET=OFF', '-DPython3_EXECUTABLE=' + str(python)]
    cmd(args, 'configure', 240)
    cache = (B / 'CMakeCache.txt').read_text()
    for row in ['ENABLE_WALLET:BOOL=ON', 'WITH_SQLITE:BOOL=ON', 'BUILD_DAEMON:BOOL=ON', 'BUILD_CLI:BOOL=ON', 'BUILD_GUI:BOOL=OFF', 'BUILD_TESTS:BOOL=OFF', 'WITH_MODELNET:BOOL=OFF']:
        assert row in cache
    shutil.copy2(B / 'CMakeCache.txt', R / 'CMakeCache.txt')
    config = B / 'test/config.ini'
    assert config.is_file(), 'Missing functional-runner configuration'
    generated = configparser.ConfigParser()
    generated.read(config)
    for flag in ['ENABLE_WALLET', 'USE_SQLITE', 'ENABLE_BITCOIND', 'ENABLE_CLI']:
        assert generated['components'].getboolean(flag)
    assert not generated['components'].getboolean('ENABLE_MODELNET', fallback=False)
    assert Path(generated['environment']['SRCDIR']).resolve() == S
    assert Path(generated['environment']['BUILDDIR']).resolve() == B
    shutil.copy2(config, R / 'config.ini')
    plan = cmd(['ninja', '-C', B, '-n', 'btxd', 'btx-cli'], 'actual-plan')
    assert 'Re-running CMake' not in plan
    edges = sum(line.startswith('[') for line in plan.splitlines())
    STATE['actual_edges'] = edges
    assert edges <= 1000, 'Plan exceeds bounded two-target allowance; retain checkpoint'
    commands = cmd(['ninja', '-C', B, '-t', 'commands', 'btxd', 'btx-cli'], 'generated-commands')
    selected = {}
    command_tokens = shlex.split(commands)
    for library, expected in M['openssl_static_sha256'].items():
        refs = [token for token in command_tokens if library in token]
        if refs:
            paths = {token for token in refs if Path(token).is_absolute() and token.endswith('/' + library)}
            assert len(paths) == 1 and all(token in paths for token in refs), 'Unresolved selected archive path'
            archive = Path(next(iter(paths)))
            assert archive.is_file()
            selected[library] = {'path': str(archive), 'resolved': str(archive.resolve()), 'sha256': sha(archive)}
            assert selected[library]['sha256'] == expected, 'Selected static dependency drift'
    STATE['selected_openssl'] = selected
    STATE['embedded_python_selected'] = 'Python.framework' in commands or '-lpython' in commands
    STATE['python_dependency_commands_recorded'] = True
    assert shutil.disk_usage(W).free > preservation_floor()
    save()
    if os.environ.get('BUILD_APPROVED') == 'true':
        cmd(['ninja', '-C', B, '-j2', 'btxd', 'btx-cli'], 'build', 1200)
        STATE['compiled'] = True
        STATE['binaries'] = {n: {'sha256': sha(B / 'bin' / n), 'bytes': (B / 'bin' / n).stat().st_size}
                             for n in ['btxd', 'btx-cli']}
        for name in STATE['binaries']:
            cmd(['file', B / 'bin' / name], name + '-format')
            cmd(['otool', '-L', B / 'bin' / name], name + '-dependencies')
        assert all('arm64' in (R / (name + '-format.log')).read_text() for name in STATE['binaries'])
    # Deliberately no binary invocation, test execution, overlay application or runtime data.
    STATE['complete'] = True

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        STATE['error'] = str(error)
        raise
    finally:
        save()
