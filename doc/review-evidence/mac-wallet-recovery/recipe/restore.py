"""Retained restore helpers only; copied unchanged function bodies from the reviewed build recipe. No configure/build entry point."""
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
    return sum(p.stat().st_size for root in (S, B, W / 'job-deps') if root.exists()
               for p in root.rglob('*') if p.is_file() and not p.is_symlink()
               and '.git' not in p.relative_to(W).parts)

def preservation_floor():
    # Keep room for a worst-case compressed checkpoint plus 3GiB margin,
    # and a further 512MiB while a command is being stopped.
    return max(RESERVE, live_bytes() + 3 * 1024**3 + 512 * 1024**2)

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
            if not member.name.startswith(('mac-config-build/', 'job-deps/')):
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
    selected = {n for n in inv if n.startswith(('mac-config-build/', 'job-deps/'))}
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
