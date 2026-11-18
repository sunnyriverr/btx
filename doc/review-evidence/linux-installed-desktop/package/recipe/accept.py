"""Prepared, UNEXECUTED exact-archive installed desktop acceptance controller.

Only run after explicit hosted-run authorization. Session2 recipe adapted to one
installed prefix; no model transfer/inference, build, signing or wallet actions.
"""
import argparse
import hashlib
import json
import os
import platform
import shutil
import signal
import stat
import subprocess
import tarfile
import time
import traceback
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def snapshot(root):
    result = {}
    for p in sorted(root.rglob('*')):
        name = p.relative_to(root).as_posix()
        mode = oct(stat.S_IMODE(p.lstat().st_mode))
        if p.is_symlink():
            result[name] = {'type': 'symlink', 'target': os.readlink(p), 'mode': mode}
        elif p.is_file():
            result[name] = {'type': 'file', 'sha256': sha(p), 'size': p.stat().st_size, 'mode': mode}
        elif p.is_dir():
            result[name] = {'type': 'directory', 'mode': mode}
        else:
            raise ValueError('Unexpected installed member: ' + name)
    return result


def processes(prefix, ownership=None):
    rows = []
    sessions = {}
    if ownership is not None and ownership.is_file():
        for leader in json.loads(ownership.read_text()):
            assert leader['pid'] == leader['session'] and int(leader['start_ticks']) > 0
            try:
                live = (Path('/proc') / str(leader['pid']) / 'stat').read_text().rsplit(')', 1)[1].split()
                # Reject a recycled leader PID; never expand ownership to it.
                if live[19] != leader['start_ticks']:
                    continue
            except FileNotFoundError:
                pass  # Descendants can retain the session after its leader exits.
            sessions[leader['session']] = int(leader['start_ticks'])
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():
            continue
        try:
            exe = Path(os.readlink(p / 'exe'))
            fields = (p / 'stat').read_text().rsplit(')', 1)[1].split()
            session = int(fields[3])
            # This exact unique installed tree is never shared with another job.
            if (exe.is_relative_to(prefix) or
                    (session in sessions and int(fields[19]) >= sessions[session])):
                rows.append({'pid': int(p.name), 'exe': str(exe), 'start_ticks': fields[19],
                             'session': session})
        except (OSError, ValueError):
            pass
    return rows


def bounded(args, log, timeout, env, grace=60):
    with log.open('wb') as f:
        proc = subprocess.Popen([str(x) for x in args], stdout=f, stderr=subprocess.STDOUT,
                                env=env, start_new_session=True)
        try:
            return proc.wait(timeout=timeout)
        except BaseException:
            # Child drivers own their ordinary cleanup; timeout is never PASS.
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=grace)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait(timeout=5)
            raise


def admit(outer, root, pins):
    assert outer.stat().st_size == pins['outer_bytes']
    assert sha(outer) == pins['outer_sha256'], 'Outer artifact digest mismatch'
    dest = root / 'input'
    dest.mkdir()
    with zipfile.ZipFile(outer) as z:
        names = z.namelist()
        assert len(names) == len(set(names))
        assert sum(x.file_size for x in z.infolist()) < 190 * 1024**2
        for n in names:
            path = Path(n)
            assert not path.is_absolute() and '..' not in path.parts
        z.extractall(dest)
    archive = dest / pins['archive_name']
    assert archive.stat().st_size == pins['archive_bytes']
    assert sha(archive) == pins['archive_sha256'], 'Inner archive digest mismatch'
    for n, expected in pins['pins'].items():
        assert sha(dest / n) == expected, 'Producer record changed: ' + n
    provenance = json.loads((dest / 'provenance.json').read_text())
    assert provenance['source'] == pins['source']
    assert provenance['archive_sha256'] == pins['archive_sha256']
    patch = provenance['packaging_implementation']['patch']
    assert patch['patch_sha256'] == pins['packaging_patch_sha256']
    assert patch['candidate_sha256'] == pins['bundler_sha256']
    assert sha(HERE / 'source/install.sh') == pins['installer_sha256']
    # Retain tar member types/modes/hashes rather than trusting a successful extraction.
    expected = json.loads((dest / 'members.json').read_text())
    # Producer manifests retain the archive root under its full name, while
    # child entries are relative to it. Filesystem snapshots omit that root.
    root_entry = expected.pop(pins['root'])
    assert root_entry['type'] == 'directory' and root_entry['size'] == 0
    extracted = root / 'extracted'
    extracted.mkdir()
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
        assert len(members) < 2000 and sum(x.size for x in members) < 2 * 1024**3
        seen = set()
        for m in members:
            path = Path(m.name)
            assert not path.is_absolute() and '..' not in path.parts
            assert path.parts[0] == pins['root']
            assert m.name not in seen
            seen.add(m.name)
            assert m.isfile() or m.isdir() or m.issym() or m.islnk()
            relative = path.relative_to(pins['root']).as_posix()
            if relative == '.':
                assert m.isdir()
                assert m.size == root_entry['size'] and oct(m.mode) == root_entry['mode']
                continue
            want = expected[relative]
            kind = ('file' if m.isfile() else 'directory' if m.isdir()
                    else 'symlink' if m.issym() else 'hardlink')
            assert kind == want['type'] and m.size == want['size']
            assert oct(m.mode) == want['mode']
            if m.issym() or m.islnk():
                assert m.linkname == want['target']
                assert hashlib.sha256(m.linkname.encode()).hexdigest() == want['link_text_sha256']
        tar.extractall(extracted, filter='data')
    unpacked = extracted / pins['root']
    unpacked.chmod(int(root_entry['mode'], 8))
    # data_filter intentionally ignores directory modes. Restore only the
    # admitted manifest's modes inside this private parent, before comparison.
    for n, want in expected.items():
        if want['type'] == 'directory':
            (unpacked / n).chmod(int(want['mode'], 8))
    actual = snapshot(unpacked)
    assert set(actual) == set(expected), 'Archive member set differs'
    for n, want in expected.items():
        got = actual[n]
        assert got['mode'] == want['mode'], 'Archive mode mismatch: ' + n
        if want['type'] in ('file', 'hardlink'):
            assert got['type'] == 'file' and got['sha256'] == want['sha256']
        elif want['type'] == 'symlink':
            assert got['type'] == 'symlink' and got['target'] == want['target']
        else:
            assert got['type'] == want['type']
    return unpacked, archive, provenance


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifact', required=True, type=Path)
    parser.add_argument('--runtime', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    assert os.environ.get('BTX_DESKTOP_ACCEPTANCE') == 'authorized-disposable-run'
    root, out = args.runtime.absolute(), args.out.absolute()
    assert root.is_relative_to(Path(os.environ['RUNNER_TEMP']).resolve())
    assert not out.is_relative_to(root) and not root.is_relative_to(out)
    assert not root.exists() and not out.exists()
    out.mkdir(parents=True)
    root.mkdir(mode=0o700)
    pins = json.loads((HERE / 'inputs.json').read_text())
    state = {'overall': 'FAIL', 'scope': pins['scope'], 'phases': {},
             'source': pins['source'], 'archive_sha256': pins['archive_sha256'],
             'fixture_commit': os.environ['GITHUB_SHA'], 'cleanup_signals': [],
             'rebuild': False, 'release_qualified': False}
    prefix = root / 'installed'
    ownership = out / 'gui/owned-sessions.json'
    before = None
    def interrupted(signum, _frame):
        raise InterruptedError('Controller signal ' + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        assert platform.machine() == 'x86_64'
        os_release = Path('/etc/os-release').read_text()
        assert 'VERSION_ID="24.04"' in os_release
        assert shutil.disk_usage(root).free > 4 * 1024**3
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        for k in ('LD_PRELOAD', 'LD_LIBRARY_PATH', 'PYTHONHOME', 'PYTHONPATH',
                  'BTX_MODELD', 'BTX_MODELHELPER', 'BTX_GUARDD'):
            env.pop(k, None)
        unpacked, archive, provenance = admit(args.artifact, root, pins)
        state['phases']['artifact'] = 'PASS'
        state['producer'] = {'run': pins['producer_run'], 'artifact': pins['artifact_id'],
                             'outer_sha256': pins['outer_sha256'], 'components': provenance['components']}
        # Upstream staging runs only its version probes; it copies bin/libexec/lib.
        code = bounded(['bash', HERE / 'install-tree.sh', HERE, unpacked, prefix, root / 'installer'],
                       out / 'installer.log', 90, env)
        assert code == 0, 'Prebuilt-tree install failed'
        before = snapshot(prefix)
        source_files = snapshot(unpacked)
        expected = {n: v for n, v in source_files.items()
                    if n.split('/')[0] in ('bin', 'lib', 'libexec')}
        assert {n: v for n, v in before.items() if n != 'manifest.json'} == expected
        manifest = json.loads((prefix / 'manifest.json').read_text())
        assert manifest['git_commit'] == pins['source'] and manifest['source'] == 'prebuilt'
        state['installer_manifest'] = manifest
        state['phases']['installed_tree'] = 'PASS'
        assert not processes(prefix)
        for name, seconds in (('gui', 300), ('lifecycle', 240)):
            phase_out = out / name
            phase_out.mkdir()
            code = bounded(['/usr/bin/python3', HERE / (name + '.py'), '--prefix', prefix,
                            '--runtime', root / name, '--out', phase_out],
                           out / (name + '-driver.log'), seconds, env,
                           grace=100 if name == 'gui' else 60)
            result = json.loads((phase_out / 'result.json').read_text())
            assert code == 0 and result['overall'] == 'PASS', name + ' failed'
            assert snapshot(prefix) == before, name + ' changed installed payload'
            assert not processes(prefix, ownership), name + ' left owned processes'
            state['phases'][name] = 'PASS'
        assert sha(archive) == pins['archive_sha256']
        assert sha(args.artifact) == pins['outer_sha256']
        state['phases']['unchanged_payload'] = 'PASS'
    except BaseException:
        state['error'] = traceback.format_exc()
    finally:
        # Emergency cleanup targets only current processes under our unique prefix.
        for sig in (signal.SIGTERM, signal.SIGKILL):
            owned = processes(prefix, ownership)
            for row in owned:
                if row in processes(prefix, ownership):
                    try:
                        os.kill(row['pid'], sig)
                        state['cleanup_signals'].append({'pid': row['pid'], 'signal': sig.name})
                    except ProcessLookupError:
                        pass
            if owned:
                time.sleep(2)
        state['cleanup_remaining'] = processes(prefix, ownership)
        state['payload_unchanged'] = before is not None and snapshot(prefix) == before
        if not state['cleanup_remaining']:
            shutil.rmtree(root)
        state['runtime_removed'] = not root.exists()
        wanted = {'artifact', 'installed_tree', 'gui', 'lifecycle', 'unchanged_payload'}
        if (set(state['phases']) == wanted and set(state['phases'].values()) == {'PASS'}
                and 'error' not in state and state['payload_unchanged']
                and not state['cleanup_signals'] and not state['cleanup_remaining']
                and state['runtime_removed']):
            state['overall'] = 'PASS'
        (out / 'result.json').write_text(json.dumps(state, indent=2) + '\n')
    return 0 if state['overall'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
