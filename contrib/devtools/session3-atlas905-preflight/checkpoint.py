"""Retain only isolated Rust state after the compiler process group is gone."""
import hashlib
from itertools import chain
import json
import os
from pathlib import Path
import shutil
import sys
import tarfile
import tempfile
import time
from restore import safe_name, PIN


def main():
    workspace = Path(os.environ['GITHUB_WORKSPACE']).resolve()
    records = Path(os.environ['RECORDS']).resolve()
    result = {'status': 'CHECKPOINT_NOT_ADMITTED', 'source': PIN['source']}
    deadline = time.monotonic() + 360
    def tick():
        if time.monotonic() >= deadline:
            raise TimeoutError('checkpoint bound')
        if shutil.disk_usage(workspace).free < 2 * 1024**3:
            raise OSError('disk reserve')
    def digest(path):
        h = hashlib.sha256()
        with path.open('rb') as stream:
            for data in iter(lambda: stream.read(1024 * 1024), b''):
                tick()
                h.update(data)
        return h.hexdigest()
    try:
        # A failed/missing prerequisite is not permission to inspect unrelated roots.
        build_path = records / 'build-result.json'
        if not build_path.is_file():
            return 0
        build = json.loads(build_path.read_text())
        if not build.get('compile_started'):
            return 0
        if build.get('process_cleanup') is not True:
            raise ValueError('compiler cleanup unproven')
        assert json.loads((records / 'restore-result.json').read_text())['status'] == 'PASS_RESTORE_ONLY'
        assert json.loads((records / 'preflight-result.json').read_text())['status'] == 'PASS_RESTORE_AND_PREFLIGHT_ONLY'
        owned = json.loads((records / 'owned-roots.json').read_text())
        roots = {'atlas480-cargo', 'atlas480-target'}
        assert owned['workspace'] == str(workspace) and owned['artifact'] == PIN['artifact'] and set(owned['roots']) == roots
        paths = []
        total = 0
        for root in sorted(roots):
            base = workspace / root
            assert base.is_dir() and not base.is_symlink()
            for path in chain([base], base.rglob('*')):
                tick()
                safe_name(path.relative_to(workspace).as_posix())
                assert not path.is_symlink() and (path.is_dir() or path.is_file())
                if path.is_file():
                    total += path.stat().st_size
                paths.append(path)
                assert len(paths) <= PIN['limits']['max_entries'] and total <= PIN['limits']['max_restored_bytes']
        assert shutil.disk_usage(workspace).free >= int(total * 1.02) + PIN['limits']['reserve_bytes']
        rows = {}
        with tempfile.TemporaryDirectory(prefix='atlas905-checkpoint-', dir=os.environ['RUNNER_TEMP']) as temp:
            ready = Path(temp) / 'ready'
            ready.mkdir()
            archive = ready / 'state.tar.gz'
            with tarfile.open(archive, 'w:gz', compresslevel=1) as tar:
                for path in paths:
                    tick()
                    name = path.relative_to(workspace).as_posix()
                    if path.is_file():
                        info = path.stat()
                        assert (info.st_mode & 0o777) in {0o600, 0o640, 0o644, 0o755}
                        rows[name] = {'sha256': digest(path), 'mode': oct(info.st_mode & 0o777),
                                      'mtime_ns': info.st_mtime_ns, 'bytes': info.st_size}
                    tar.add(path, arcname=name, recursive=False)
            inner_digest = digest(archive)
            # Re-read the completed stream: no unchecked archive is marked ready.
            seen = set()
            with tarfile.open(archive, 'r|gz') as tar:
                for member in tar:
                    tick()
                    safe_name(member.name)
                    if member.isdir():
                        continue
                    assert member.name in rows and member.name not in seen
                    if member.islnk():
                        assert member.linkname in seen and rows[member.linkname]['sha256'] == rows[member.name]['sha256']
                    else:
                        assert member.isfile() and member.size == rows[member.name]['bytes']
                        h = hashlib.sha256()
                        with tar.extractfile(member) as stream:
                            for data in iter(lambda: stream.read(1024 * 1024), b''):
                                tick()
                                h.update(data)
                        assert h.hexdigest() == rows[member.name]['sha256']
                    seen.add(member.name)
            assert seen == set(rows)
            manifest = {'source': PIN['source'], 'workspace': str(workspace), 'toolchain': PIN['toolchain'],
                        'archive_sha256': inner_digest, 'files': rows, 'parent_artifact': PIN['artifact'],
                        'archive_members_verified': True, 'restore_verified': False,
                        'build_status': build['status']}
            (ready / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
            final = Path(os.environ['RUNNER_TEMP']) / 'session3-atlas905-checkpoint'
            assert not final.exists()
            ready.rename(final)
            result.update(status='PASS_CHECKPOINT_RETAINED_NOT_RESTORED', files=len(rows),
                          archive_sha256=inner_digest, archive_bytes=(final / 'state.tar.gz').stat().st_size,
                          plain_bytes=total, manifest_sha256=digest(final / 'manifest.json'),
                          restore_verified=False, parent_artifact=PIN['artifact'], build_status=build['status'])
    except Exception as error:
        result['status'] = 'FAIL_CHECKPOINT'
        result['error_class'] = type(error).__name__
    finally:
        (records / 'checkpoint-result.json').write_text(json.dumps(result, indent=2) + '\n')
    return 1 if result['status'] == 'FAIL_CHECKPOINT' else 0


if __name__ == '__main__':
    sys.exit(main())
