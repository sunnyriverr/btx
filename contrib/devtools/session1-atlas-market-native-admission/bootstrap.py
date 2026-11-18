"""Future hosted-only dependency staging; not executed during source preparation."""
from pathlib import Path, PurePosixPath
import hashlib, json, os, platform, shutil, subprocess, tarfile, urllib.request, urllib.error, urllib.parse

W = Path(os.environ['GITHUB_WORKSPACE']).resolve()
P = Path(__file__).resolve().parent
D, R, INPUT = W / 'job-deps', W / 'records', W / 'dependency-inputs'
RESERVE = 1342177280

def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None

def response(row):
    url = row['url']
    assert urllib.parse.urlparse(url).scheme == 'https'
    host = urllib.parse.urlparse(url).hostname
    if host == 'ghcr.io':
        scope = 'repository:' + row['registry_repository'] + ':pull'
        query = urllib.parse.urlencode({'service': 'ghcr.io', 'scope': scope})
        with urllib.request.urlopen('https://ghcr.io/token?' + query, timeout=30) as f:
            token = json.load(f)['token']
        req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + token})
        try:
            return urllib.request.build_opener(NoRedirect).open(req, timeout=60)
        except urllib.error.HTTPError as error:
            assert error.code in (301, 302, 303, 307, 308)
            target = error.headers['Location']
            assert target.startswith('https://')
            return urllib.request.urlopen(target, timeout=60)  # No auth forwarded.
    assert host == 'files.pythonhosted.org'
    return urllib.request.urlopen(url, timeout=60)

def download(row, path, limit):
    total = 0
    with response(row) as src, path.open('wb') as out:
        while True:
            block = src.read(1048576)
            if not block:
                break
            total += len(block)
            assert total <= limit and shutil.disk_usage(W).free > RESERVE
            out.write(block)
    assert sha(path) == row['sha256'], 'Dependency archive digest mismatch'

def main():
    assert os.environ.get('GITHUB_ACTIONS') == 'true'
    assert platform.system() == 'Darwin' and platform.machine() == 'arm64'
    R.mkdir(exist_ok=True)
    INPUT.mkdir(exist_ok=True)
    lock = json.loads((P / 'dependencies.json').read_text())
    locksha = sha(P / 'dependencies.json')
    receipt = D / 'dependency-manifest.json'
    if receipt.exists():
        saved = json.loads(receipt.read_text())
        assert saved['lock_sha256'] == locksha, 'Changed dependency lock requires fresh owned prefix'
        files = {str(p.relative_to(D)) for p in D.rglob('*') if p.is_file() and p != receipt}
        assert files == set(saved['files'])
        assert all(not (D / n).is_symlink() and sha(D / n) == h for n, h in saved['files'].items())
    else:
        # Only this fixed, owned ephemeral dependency prefix is disposable.
        assert D.parent == W and D.name == 'job-deps' and not D.is_symlink()
        if D.exists():
            shutil.rmtree(D)
        D.mkdir()
        extracted = 0
        for row in lock['bottles']:
            archive = INPUT / (row['name'].replace('@', '-') + '.tar.gz')
            download(row, archive, 160 * 1024**2)
            root = PurePosixPath(row['tar_root'])
            seen = set()
            with tarfile.open(archive) as t:
                for member in t:
                    path = PurePosixPath(member.name)
                    assert not path.is_absolute() and '..' not in path.parts
                    assert member.name not in seen
                    seen.add(member.name)
                    if not path.is_relative_to(root):
                        continue
                    rel = path.relative_to(root)
                    if row['name'] == 'boost@1.85':
                        keep = len(rel.parts) >= 3 and rel.parts[:2] == ('include', 'boost')
                    else:
                        keep = (len(rel.parts) >= 2 and rel.parts[0] == 'include') or str(rel) in (
                            'lib/libevent_core.a', 'lib/libevent_extra.a', 'lib/libevent_pthreads.a')
                    if not keep or member.isdir():
                        continue
                    assert member.isfile() and member.size <= 16 * 1024**2
                    extracted += member.size
                    assert extracted <= 512 * 1024**2 and shutil.disk_usage(W).free > RESERVE
                    dest = D / str(rel)
                    assert dest.parent.resolve().is_relative_to(D)
                    assert not dest.exists(), 'Duplicate selected dependency member'
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with t.extractfile(member) as src, dest.open('wb') as out:
                        shutil.copyfileobj(src, out, 1048576)
                    dest.chmod(0o644)
            archive.unlink()
        required = ['include/boost/version.hpp', 'include/event2/event.h', 'include/event2/http.h',
                    'lib/libevent_core.a', 'lib/libevent_extra.a', 'lib/libevent_pthreads.a']
        assert all((D / n).is_file() for n in required), 'Pinned bottle lacks required static/header payload'
        assert '#define BOOST_VERSION 108500' in (D / 'include/boost/version.hpp').read_text()
        saved = {'lock_sha256': locksha, 'files': {str(p.relative_to(D)): sha(p)
                 for p in D.rglob('*') if p.is_file()}, 'profile': lock['profile']}
        receipt.write_text(json.dumps(saved, indent=2) + '\n')
    # Install exact binary wheels only into the setup-python runtime owned by this ephemeral job.
    python = Path(os.environ['BTX_BUILD_PYTHON'])
    assert python.is_absolute() and python.is_file()
    probe = subprocess.check_output([str(python), '-I', '-c',
        'import json,platform,sys;print(json.dumps([list(sys.version_info[:3]),platform.machine(),sys.prefix]))'], text=True)
    version, arch, prefix = json.loads(probe)
    assert version == [3, 12, 10] and arch == 'arm64' and prefix != '/usr'
    lines = []
    for row in lock['wheels']:
        target = INPUT / row['wheel']
        download(row, target, 32 * 1024**2)
        lines.append(row['package'] + '==' + row['version'] + ' --hash=sha256:' + row['sha256'])
    requirements = INPUT / 'requirements.lock'
    requirements.write_text('\n'.join(lines) + '\n')
    subprocess.run([str(python), '-m', 'pip', 'install', '--no-index', '--find-links', str(INPUT),
                    '--only-binary=:all:', '--no-deps', '--no-compile', '--require-hashes',
                    '--force-reinstall', '-r', str(requirements)], check=True, timeout=120)
    modules = subprocess.check_output([str(python), '-I', '-c',
        'import json,cryptography,cffi,pycparser,sqlite3;from cryptography.hazmat.primitives.ciphers.aead import AESGCM;'
        'print(json.dumps(dict(cryptography=cryptography.__version__,cffi=cffi.__version__,'
        'pycparser=pycparser.__version__,sqlite=sqlite3.sqlite_version)))'], text=True)
    installed = json.loads(modules)
    assert [installed[k] for k in ('cryptography', 'cffi', 'pycparser')] == ['46.0.4', '2.1.1', '3.12']
    (R / 'dependency-bootstrap.json').write_text(json.dumps(
        {'lock_sha256': locksha, 'prefix': str(D), 'python_modules': installed,
         'selected_files': saved['files'], 'no_source_dependency_build': True}, indent=2) + '\n')

if __name__ == '__main__':
    main()
