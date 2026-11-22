"""Restore pinned public Rust inputs only; never execute retained outputs."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import signal
import tarfile
import tempfile
import sys
import urllib.parse
import urllib.request
import zipfile

HERE = Path(__file__).resolve().parent
PIN = json.loads((HERE / 'INPUTS.json').read_text())
ROOTS = {'atlas480-cargo', 'atlas480-target'}


def require(ok, label):
    if not ok:
        raise ValueError(label)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def safe_name(name):
    p = PurePosixPath(name)
    require(str(p) == name and not p.is_absolute() and '..' not in p.parts
            and p.parts and p.parts[0] in ROOTS and '\\' not in name
            and not any(ord(c) < 32 for c in name), 'unsafe member name')
    require(p.name not in {'credentials', 'credentials.toml'}, 'unexpected credential file')
    return p


class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, *args):
        redirected = super().redirect_request(request, *args)
        if redirected:
            require(redirected.full_url.startswith('https://'), 'non-HTTPS redirect')
            if urllib.parse.urlparse(redirected.full_url).netloc != 'api.github.com':
                redirected.remove_header('Authorization')
        return redirected


def request(endpoint):
    req = urllib.request.Request('https://api.github.com/repos/sunnyriverr/btx/' + endpoint,
        headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
                 'Accept': 'application/vnd.github+json', 'User-Agent': 'BTX-Atlas905-preflight'})
    return urllib.request.build_opener(Redirect).open(req, timeout=60)


def main():
    workspace = Path(os.environ['GITHUB_WORKSPACE']).resolve()
    records = Path(os.environ['RECORDS']).resolve()
    result = {'status': 'FAIL_RESTORE', 'phase': 'admission', 'executed_cache': False}
    def save():
        temporary = records / 'restore-result.tmp'
        temporary.write_text(json.dumps(result, indent=2) + '\n')
        temporary.replace(records / 'restore-result.json')
        print(json.dumps({'restore_phase': result['phase'],
                          'verified_files': result.get('files_verified', 0)}), flush=True)
    def phase(label):
        result['phase'] = label
        save()
    def interrupted(signum, frame):
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, signal.SIG_IGN)
        result['interrupt_signal'] = signum
        raise InterruptedError('restore interrupted')
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, interrupted)
    try:
        save()
        require(str(workspace) == PIN['producer_workspace'], 'workspace prefix differs')
        require(all(not (workspace / root).exists() and not (workspace / root).is_symlink()
                    for root in ROOTS), 'restore roots already exist')
        require(shutil.disk_usage(workspace).free >= 10 * 1024**3, '10GiB admission floor')
        with request('actions/artifacts/' + str(PIN['artifact'])) as response:
            meta = json.load(response)
        require(not meta['expired'] and meta['size_in_bytes'] == PIN['outer_bytes']
                and meta['digest'] == 'sha256:' + PIN['outer_sha256'], 'artifact metadata mismatch')
        with tempfile.TemporaryDirectory(prefix='atlas905-download-', dir=os.environ['RUNNER_TEMP']) as temp:
            archive = Path(temp) / 'artifact.zip'
            phase('download')
            count = 0
            with request('actions/artifacts/' + str(PIN['artifact']) + '/zip') as response, archive.open('xb') as output:
                for block in iter(lambda: response.read(1024 * 1024), b''):
                    count += len(block)
                    require(count <= PIN['outer_bytes'], 'outer size bound')
                    output.write(block)
            require(count == PIN['outer_bytes'] and digest(archive) == PIN['outer_sha256'], 'outer integrity')
            inner = Path(temp) / 'state.tar.gz'
            with zipfile.ZipFile(archive) as z:
                require(sorted(z.namelist()) == ['manifest.json', 'state.tar.gz'], 'unexpected ZIP members')
                require(z.getinfo('manifest.json').file_size <= PIN['limits']['max_manifest_bytes'], 'manifest bound')
                require(z.getinfo('state.tar.gz').file_size <= PIN['limits']['max_inner_bytes'], 'inner bound')
                manifest_bytes = z.read('manifest.json')
                require(hashlib.sha256(manifest_bytes).hexdigest() == PIN['manifest_sha256'], 'manifest integrity')
                with z.open('state.tar.gz') as source, inner.open('xb') as output:
                    shutil.copyfileobj(source, output, 1024 * 1024)
            require(digest(inner) == PIN['inner_sha256'], 'inner integrity')
            manifest = json.loads(manifest_bytes)
            require(manifest['source'] == PIN['producer_source']
                    and manifest['workspace'] == str(workspace)
                    and manifest['toolchain'] == PIN['toolchain']
                    and manifest['archive_sha256'] == PIN['inner_sha256'], 'producer identity')
            rows = manifest['files']
            require(len(rows) == PIN['manifest_files'], 'manifest file count')
            for name, row in rows.items():
                safe_name(name)
                require(row['mode'] in {'0o600', '0o640', '0o644', '0o755'}
                        and type(row['mtime_ns']) is int and 0 <= row['mtime_ns'] <= 2**63 - 1
                        and len(row['sha256']) == 64, 'manifest fields')
            phase('tar admission')
            entries = {}
            with tarfile.open(inner, 'r:gz') as tar:
                for member in tar:
                    safe_name(member.name)
                    require(member.name not in entries and len(entries) < PIN['limits']['max_entries'], 'entry bound/duplicate')
                    require(member.isdir() or member.isfile() or member.issym() or member.islnk(), 'special member')
                    entries[member.name] = member
                regular = {k for k, v in entries.items() if v.isfile() or v.islnk()}
                require(regular == set(rows), 'regular member set differs')
                total = 0
                for name, member in entries.items():
                    for parent in PurePosixPath(name).parents:
                        if str(parent) in entries:
                            require(entries[str(parent)].isdir(), 'non-directory ancestor')
                    if member.islnk():
                        safe_name(member.linkname)
                        require(member.linkname in rows and entries[member.linkname].isfile()
                                and rows[name]['sha256'] == rows[member.linkname]['sha256'], 'hardlink target')
                        total += entries[member.linkname].size
                    elif member.isfile():
                        total += member.size
                    if member.issym():
                        # Symlinks are not needed for crate admission. Fail closed
                        # rather than restore a link omitted by the legacy manifest.
                        raise ValueError('legacy unmanifested symlink requires review')
                    require(total <= PIN['limits']['max_restored_bytes'], 'restored byte bound')
                require(shutil.disk_usage(workspace).free >= total + PIN['limits']['reserve_bytes'], 'restore capacity')
            # Close the complete admission scan before reading data. A second
            # forward-only stream keeps decompression linear in archive size.
            phase('restore regular files')
            owned = {'workspace': str(workspace), 'artifact': PIN['artifact'], 'roots': []}
            marker = records / 'owned-roots.json'
            marker.write_text(json.dumps(owned) + '\n')
            for root in sorted(ROOTS):
                (workspace / root).mkdir(exist_ok=False)
                owned['roots'].append(root)
                temporary = marker.with_suffix('.tmp')
                try:
                    temporary.write_text(json.dumps(owned) + '\n')
                    temporary.replace(marker)
                except Exception:
                    # This root was just created and is still empty.
                    (workspace / root).rmdir()
                    raise
            restored = set()
            deferred_links = []
            seen = set()
            result['files_verified'] = 0
            def finish_file(name, target):
                require(digest(target) == rows[name]['sha256'], 'restored member integrity')
                target.chmod(int(rows[name]['mode'], 8))
                os.utime(target, ns=(rows[name]['mtime_ns'], rows[name]['mtime_ns']))
                restored.add(name)
                result['files_verified'] = len(restored)
                if len(restored) % 500 == 0:
                    save()
            with tarfile.open(inner, 'r|gz') as tar:
                for member in tar:
                    require(member.name in entries and member.name not in seen,
                            'stream member set differs')
                    seen.add(member.name)
                    admitted = entries[member.name]
                    require((member.type, member.size, member.linkname) ==
                            (admitted.type, admitted.size, admitted.linkname),
                            'stream member identity differs')
                    if member.isdir():
                        continue
                    if member.islnk():
                        deferred_links.append(member.name)
                        continue
                    require(member.isfile(), 'stream member type')
                    target = workspace / member.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with tar.extractfile(member) as source, target.open('xb') as output:
                        shutil.copyfileobj(source, output, 1024 * 1024)
                    finish_file(member.name, target)
            require(seen == set(entries), 'stream missing admitted member')
            phase('restore hardlink copies')
            for name in deferred_links:
                member = entries[name]
                require(member.linkname in restored, 'hardlink target not restored')
                target = workspace / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with (workspace / member.linkname).open('rb') as source, target.open('xb') as output:
                    shutil.copyfileobj(source, output, 1024 * 1024)
                finish_file(name, target)
            require(restored == set(rows), 'restored member set differs')
            # Receipt needed for the next step; no credentials or URLs retained.
            (records / 'restore-manifest.json').write_bytes(manifest_bytes)
            result.update(status='PASS_RESTORE_ONLY', phase='complete', files_verified=len(rows),
                          plain_bytes=total, outer_sha256=PIN['outer_sha256'], inner_sha256=PIN['inner_sha256'])
    except Exception as error:
        result['status'] = 'FAIL_RESTORE'
        result['error_class'] = type(error).__name__
        return 1
    finally:
        save()
    return 0


if __name__ == '__main__':
    sys.exit(main())
