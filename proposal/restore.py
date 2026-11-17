"""Restore verified test inputs only. Does not configure, build, or launch BTX."""
from pathlib import Path
import ast
import configparser
import hashlib
import json
import os
import re
import shutil
import tarfile
import time
import urllib.request
import urllib.parse
import zipfile

ROOT = Path('/home/runner/work/btx/btx')
RECORDS = ROOT / 'records'


def sha(path):
    with Path(path).open('rb') as stream:
        return digest(stream)


def digest(stream):
    h = hashlib.sha256()
    for data in iter(lambda: stream.read(2**20), b''):
        h.update(data)
    return h.hexdigest()


def manifest():
    return json.loads((Path(__file__).parent / 'manifest.json').read_text())


def save(name, value):
    (RECORDS / name).write_text(json.dumps(value, indent=2) + '\n')


class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, url):
        result = super().redirect_request(request, fp, code, message, headers, url)
        if result and urllib.parse.urlparse(url).netloc != 'api.github.com':
            result.remove_header('Authorization')
        return result


def get(path):
    request = urllib.request.Request('https://api.github.com/' + path, headers={
        'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
        'Accept': 'application/vnd.github+json', 'User-Agent': 'BTX-payment-preview-input-restore'})
    return urllib.request.build_opener(Redirect).open(request, timeout=30)


def selection(source, m):
    """Static selection/case inventory; never import the test framework here."""
    runner = ast.parse((source / 'test/functional/test_runner.py').read_text())
    names = []
    for node in runner.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in
                ('BASE_SCRIPTS', 'EXTENDED_SCRIPTS', 'BTX_BASE_SCRIPTS') for t in node.targets):
            names += [n.value for n in ast.walk(node.value) if isinstance(n, ast.Constant)
                      and isinstance(n.value, str)]
    picked = list(dict.fromkeys(n for n in names if n.startswith('wallet_send_psbt_preview.py')))
    assert picked == m['selected'], picked
    assert [n for n in picked if re.search(m['filter'], n)] == m['selected']
    tree = ast.parse((source / 'test/functional/wallet_send_psbt_preview.py').read_text())
    cases = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == 'CASES' for t in n.targets))
    assert [[name, flags, preview] for name, flags, preview in cases] == m['cases']
    return {'selected': picked, 'case_names': [c[0] for c in cases], 'filter': m['filter']}


def current_functional_context(source, m):
    """Use the assessed current test framework with the retained native pair."""
    applied = {}
    for name, expected in m['current_functional_sources'].items():
        assert name.startswith('test/functional/') and '..' not in Path(name).parts
        incoming = Path(__file__).parent / 'current-functional' / name
        assert sha(incoming) == expected, name
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(incoming, target)
        target.chmod(int(m['current_functional_modes'][name], 8) & 0o777)
        assert sha(target) == expected, name
        applied[name] = expected
    save('functional-context.json', {'binary_source': m['source'],
         'functional_source_head': m['functional_source_head'], 'files': applied,
         'whole_current_head_binary_qualification': False})


def overlay(source, m):
    """Apply only the reviewed test-only files after full baseline verification."""
    assert set(m['overlay_sources']) == {'test/functional/test_runner.py',
                                        'test/functional/wallet_send_psbt_preview.py'}
    assert not (source / 'test/functional/wallet_send_psbt_preview.py').exists()
    applied = {}
    for name, expected in m['overlay_sources'].items():
        incoming = Path(__file__).parent / 'overlay' / name
        assert sha(incoming) == expected, name
        target = source / name
        shutil.copyfile(incoming, target)
        target.chmod(0o755)
        assert sha(target) == expected, name
        applied[name] = {'sha256': expected, 'mode': '100755'}
    save('test-overlay.json', {'baseline_source': m['source'], 'files': applied,
                              'product_sources_changed': False, 'tests_run': False})


def main():
    assert Path.cwd() == ROOT and os.environ['GITHUB_REPOSITORY'] == 'sunnyriverr/btx'
    RECORDS.mkdir(exist_ok=True)
    assert not (ROOT / 'source').exists() and not (ROOT / 'build').exists()
    assert shutil.disk_usage(ROOT).free >= 4 * 2**30
    m = manifest()
    with get('repos/btxchain/btx/git/ref/heads/release-0.34.17') as response:
        head = json.load(response)
    assert head['object']['sha'] == m['upstream_head'], 'Source head changed; reassess, do not retarget'
    with get(f"repos/sunnyriverr/btx/actions/artifacts/{m['artifact']}") as response:
        meta = json.load(response)
    assert not meta['expired'] and meta['workflow_run']['id'] == m['producer_run']
    assert meta['digest'] == 'sha256:' + m['artifact_zip_sha256']
    assert meta['size_in_bytes'] == m['artifact_zip_bytes']
    save('artifact.json', meta)
    archive = ROOT / 'checkpoint.zip'
    start = time.monotonic()
    with get(f"repos/sunnyriverr/btx/actions/artifacts/{m['artifact']}/zip") as response, archive.open('wb') as out:
        while True:
            data = response.read(2**20)
            if not data:
                break
            assert time.monotonic() - start < 300, 'Input download bound'
            assert shutil.disk_usage(ROOT).free - len(data) > 1.25 * 2**30
            out.write(data)
    assert sha(archive) == m['artifact_zip_sha256']
    (ROOT / 'build/bin').mkdir(parents=True)
    with zipfile.ZipFile(archive) as z:
        assert set(z.namelist()) == {'producer.json', 'checkpoint.tar.gz', 'btxd', 'btx-cli'}
        raw_producer = z.read('producer.json')
        assert hashlib.sha256(raw_producer).hexdigest() == m['producer_sha256']
        producer = json.loads(raw_producer)
        assert producer['status'] == 'BUILD_AND_STATIC_INSPECTION_PASS'
        assert producer['source_identity'] == m['source'] and producer['source_transition']['tree'] == m['source_tree']
        assert producer['binary_sha256'] == m['binary_sha256']
        with z.open('checkpoint.tar.gz') as stream:
            assert digest(stream) == m['checkpoint_sha256']
        for name, expected in m['binary_sha256'].items():
            target = ROOT / 'build/bin' / name
            with z.open(name) as stream, target.open('wb') as out:
                shutil.copyfileobj(stream, out)
            assert sha(target) == expected
            target.chmod(0o755)
        # Deliberately omit objects, libraries, cache and build graph: this run cannot rebuild.
        with z.open('checkpoint.tar.gz') as stream, tarfile.open(fileobj=stream, mode='r|gz') as t:
            for entry in t:
                path = Path(entry.name)
                assert not path.is_absolute() and '..' not in path.parts
                if path.parts and path.parts[0] == 'source':
                    assert entry.name != 'source/.git' and not entry.name.startswith('source/.git/')
                    t.extract(entry, path=ROOT, filter='data')
                elif entry.name == 'build/test/config.ini':
                    target = ROOT / entry.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with t.extractfile(entry) as source, target.open('wb') as out:
                        shutil.copyfileobj(source, out)
    for name, expected in producer['source_transition']['source_files_sha256'].items():
        path = ROOT / 'source' / name
        actual = 'symlink:' + os.readlink(path) if path.is_symlink() else sha(path)
        assert actual == expected, name
    for name, expected in m['baseline_sources'].items():
        assert sha(ROOT / 'source' / name) == expected
    current_functional_context(ROOT / 'source', m)
    overlay(ROOT / 'source', m)
    for name, expected in m['critical_sources'].items():
        assert sha(ROOT / 'source' / name) == expected
    config = configparser.ConfigParser()
    config.read(ROOT / 'build/test/config.ini')
    assert config['environment']['SRCDIR'] == str(ROOT / 'source')
    assert config['environment']['BUILDDIR'] == str(ROOT / 'build')
    for flag in ('ENABLE_WALLET', 'USE_SQLITE', 'ENABLE_CLI', 'ENABLE_BITCOIND'):
        assert config['components'].getboolean(flag)
    assert not config['components'].getboolean('ENABLE_MODELNET')
    (ROOT / 'build/test/functional').symlink_to(ROOT / 'source/test/functional', target_is_directory=True)
    from elf_static import inspect
    dependencies = inspect([ROOT / 'build/bin/btxd', ROOT / 'build/bin/btx-cli'], RECORDS)
    save('selection.json', selection(ROOT / 'source', m))
    save('restore-result.json', {'status': 'RESTORE_AND_STATIC_PREFLIGHT_PASS',
         'source': m['source'], 'source_tree': m['source_tree'], 'binary_sha256': m['binary_sha256'],
         'test_overlay_sha256': m['overlay_sources'], 'product_sources_changed': False,
         'functional_source_head': m['functional_source_head'], 'current_upstream_head': m['upstream_head'],
         'source_files_verified': len(producer['source_transition']['source_files_sha256']),
         'ELF_dependencies': dependencies, 'configured': False, 'compiled': False,
         'BTX_binaries_executed': False, 'tests_run': False,
         'restored_objects': 0, 'restored_wallet_data': False})


if __name__ == '__main__':
    main()
