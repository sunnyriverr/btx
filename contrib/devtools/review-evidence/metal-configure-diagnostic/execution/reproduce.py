#!/usr/bin/env python3
"""Bounded local macOS configure regression; no installs or network operations."""
import argparse, hashlib, json, os, pathlib, shutil, subprocess, tarfile, time

REV = 'cbf65894e6d61084527cd93e913a00c6794418dd'
ASSETS = pathlib.Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--repo', type=pathlib.Path, required=True)
parser.add_argument('--cmake', default='/opt/homebrew/bin/cmake')
parser.add_argument('--prefix', default='/opt/homebrew')
parser.add_argument('--phase', choices=['baseline', 'candidate'], required=True)
parser.add_argument('--work-dir', type=pathlib.Path, default=ASSETS)
args = parser.parse_args()
ROOT = args.work_dir.resolve()
ROOT.mkdir(exist_ok=True, parents=True)
SRC = ROOT / 'source'
LOGS = ROOT / 'logs'
LOGS.mkdir(exist_ok=True)
env = dict(os.environ, PATH=args.prefix + '/bin:' + os.environ['PATH'], CMAKE_BUILD_PARALLEL_LEVEL='1')
rows = []

def usage():
    total = 0
    for directory, _, filenames in os.walk(ROOT):
        for filename in filenames:
            p = pathlib.Path(directory)/filename
            try:
                if not p.is_symlink(): total += p.lstat().st_size
            except FileNotFoundError:
                pass  # CMake removes transient try-compile files while configuring.
    free = shutil.disk_usage(ROOT).free
    if free < 1.25 * 1024**3 or total > 350 * 1024**2:
        raise RuntimeError('Resource bound reached: free=%d task=%d' % (free, total))
    return free, total

def run(name, command, extra_env=None, timeout=180):
    free, size = usage()
    start = time.monotonic()
    minfree, peak = free, size
    with (LOGS / (name + '.log')).open('w') as log:
        p = subprocess.Popen([str(x) for x in command], stdout=log, stderr=subprocess.STDOUT,
                             env=dict(env, **(extra_env or {})), start_new_session=True)
        try:
            while p.poll() is None:
                time.sleep(.25)
                f, s = usage()
                minfree, peak = min(f, minfree), max(s, peak)
                if time.monotonic() - start > timeout:
                    raise RuntimeError('Command time bound reached')
        except BaseException:
            import signal
            os.killpg(p.pid, signal.SIGTERM)
            p.wait()
            raise
    row = dict(name=name, command=[str(x) for x in command], returncode=p.returncode,
               seconds=round(time.monotonic()-start, 3), min_free_bytes=minfree, peak_task_bytes=peak)
    rows.append(row)
    (LOGS / (name + '.json')).write_text(json.dumps(row, indent=2)+'\n')
    print(name, p.returncode, flush=True)
    return p.returncode, (LOGS / (name + '.log')).read_text()

def assemble():
    if SRC.exists(): return
    usage()
    SRC.mkdir()
    p = subprocess.Popen(['git', '-C', str(args.repo), 'archive', REV], stdout=subprocess.PIPE)
    with tarfile.open(fileobj=p.stdout, mode='r|') as archive:
        for member in archive:
            dest = SRC/member.name
            assert SRC in dest.resolve().parents
            if member.issym(): assert SRC in (dest.parent/member.linkname).resolve().parents
            assert not member.islnk()
            archive.extract(member, SRC)
    assert p.wait() == 0
    usage()

def configure(name, options=(), extra_env=None):
    build = ROOT / ('build-' + name)
    command = [args.cmake, '-S', SRC, '-B', build, '-G', 'Unix Makefiles',
               '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_PREFIX_PATH='+args.prefix,
               '-DWITH_MODELNET=OFF', '-DENABLE_WALLET=OFF', '-DBUILD_GUI=OFF',
               '-DBUILD_TESTS=OFF', '-DBUILD_BENCH=OFF', '-DBUILD_TX=OFF',
               '-DBUILD_UTIL=OFF', '-DBUILD_CLI=OFF', '-DBTX_ENABLE_METAL=ON']
    # WITH_ZMQ is deliberately left at its default ON. Do not bypass static libomp.
    command.extend(options)
    receipt = LOGS/(name+'.json')
    if build.exists() and receipt.exists():
        row = json.loads(receipt.read_text())
        assert row['command'] == [str(x) for x in command]
        rows.append(row)
        rc, log = row['returncode'], (LOGS/(name+'.log')).read_text()
    else:
        assert not build.exists(), 'Refusing to overwrite an interrupted previous run'
        rc, log = run(name, command, extra_env)
    for filename in ['CMakeCache.txt', 'CMakeFiles/TargetDirectories.txt']:
        p = build/filename
        if p.exists(): shutil.copyfile(p, LOGS/(name+'-'+p.name))
    return build, rc, ' '.join(log.split())

def preserve_and_remove(build):
    name = build.name.removeprefix('build-') if hasattr(str, 'removeprefix') else build.name[6:]
    # Retain cache, exact target graph and backend defines, not regenerable objects.
    saved = LOGS/(name+'-configuration')
    saved.mkdir(exist_ok=True)
    for pattern in ['CMakeFiles/CMakeConfigureLog.yaml', 'src/CMakeFiles/btx_matmul_backend.dir/flags.make',
                    'src/CMakeFiles/btx_matmul_metallib.dir/build.make']:
        path = build/pattern
        if path.exists(): shutil.copyfile(path, saved/path.name)
    probes = {}
    for p in (build/'src').glob('btx_*probe*'):
        if p.is_file(): probes[p.name] = dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    (saved/'probes.json').write_text(json.dumps(probes, indent=2)+'\n')
    shutil.rmtree(build)

assemble()
if args.phase == 'baseline':
    run('tool-xcode-select', ['/usr/bin/xcode-select', '-p'])
    run('tool-metal', ['/usr/bin/xcrun', '-sdk', 'macosx', '--find', 'metal'])
    run('tool-metallib', ['/usr/bin/xcrun', '-sdk', 'macosx', '--find', 'metallib'])
    run('tool-clang', ['/usr/bin/clang++', '--version'])
    run('tool-cmake', [args.cmake, '--version'])
    if (LOGS/'baseline.json').exists():
        row = json.loads((LOGS/'baseline.json').read_text())
        rows.append(row)
        build, rc, log = ROOT/'build-baseline', row['returncode'], (LOGS/'baseline.log').read_text()
    else:
        build, rc, log = configure('baseline')
    assert rc == 0 and 'Metal 4 compiler unavailable' in log and 'Metal MatMul' in log
    rc, log = run('baseline-required-target', [args.cmake, '--build', build, '--target',
                                           'btx_matmul_metallib', '--parallel', '1'])
    assert rc != 0 and 'unable to find utility "metal"' in log
    preserve_and_remove(build)
else:
    already_applied = subprocess.run(['patch', '--dry-run', '-R', '-p1', '-i', str(ASSETS/'metal-configure.patch')],
                                     cwd=SRC, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).returncode == 0
    if not already_applied:
        subprocess.run(['patch', '-p1', '-i', str(ASSETS/'metal-configure.patch')], cwd=SRC, check=True)
    build, rc, log = configure('candidate')
    assert rc != 0 and 'basic Metal compilation' in log and 'PRECOMPILE_KERNELS=OFF' in log
    assert 'unable to find utility "metal"' in log
    preserve_and_remove(build)
    build, rc, log = configure('precompile-off', ['-DBTX_MATMUL_METAL_PRECOMPILE_KERNELS=OFF'])
    assert rc == 0 and 'PRECOMPILE_KERNELS=OFF; MatMul Metal backend' in log
    assert not list((build/'src').glob('btx_*probe*'))
    targets = (LOGS/'precompile-off-TargetDirectories.txt').read_text()
    assert 'metallib.dir' not in targets
    preserve_and_remove(build)
    fixture = ASSETS/'xcrun-fixture.py'
    for name, mode, options in [
        ('basic-available-metal4-unsupported', 'basic', []),
        ('missing-metallib', 'missing-link', []),
        ('no-xcrun', 'reject', ['-DBTX_XCRUN_EXECUTABLE:FILEPATH=']),
        ('metal-off', 'reject', ['-DBTX_ENABLE_METAL=OFF']),
    ]:
        calls = LOGS/(name+'-calls.jsonl')
        fixture_options = [] if name == 'no-xcrun' else ['-DBTX_XCRUN_EXECUTABLE:FILEPATH='+str(fixture)]
        build, rc, log = configure(name, fixture_options+options,
                                   dict(BTX_FIXTURE_MODE=mode, BTX_FIXTURE_LOG=str(calls)))
        invocations = [json.loads(line) for line in calls.read_text().splitlines()] if calls.exists() else []
        if mode == 'basic':
            assert rc == 0 and 'Metal 4 compiler unavailable' in log
            assert len(invocations) == 3
            assert invocations[0][0:4] == ['-sdk', 'macosx', 'metal', '-c']
            assert invocations[1][0:3] == ['-sdk', 'macosx', 'metallib']
            assert '-std=metal4.0' in invocations[2]
            targets = (LOGS/(name+'-TargetDirectories.txt')).read_text()
            for t in ['btx_matmul_metallib', 'btx_oracle_metallib', 'btx_matmul_v4_metallib',
                      'btx_matmul_v4_bmx4_metallib', 'btx_rc_rowleaf_metallib', 'btx_rc_fp3_lde_metallib']:
                assert t+'.dir' in targets
            assert 'metal4_metallib.dir' not in targets and 'btx_lt_tensor_metallib.dir' not in targets
            flags = (build/'src/CMakeFiles/btx_matmul_backend.dir/flags.make').read_text()
            assert 'BTX_MATMUL_METALLIB_PATH' in flags and 'BTX_MATMUL_V4_METAL4_METALLIB_PATH' not in flags
        elif mode == 'missing-link':
            assert rc != 0 and 'metallib linking' in log and 'fixture: metallib unavailable' in log
            assert len(invocations) == 2
        else:
            assert rc == 0 and not invocations
            assert not list((build/'src').glob('btx_*probe*'))
            assert 'metallib.dir' not in (LOGS/(name+'-TargetDirectories.txt')).read_text()
            if name == 'no-xcrun': assert 'xcrun not found; MatMul Metal backend' in log
        preserve_and_remove(build)

(ROOT/(args.phase+'-results.json')).write_text(json.dumps(rows, indent=2)+'\n')
