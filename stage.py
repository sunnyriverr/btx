"""Verify the retained hosted archive and extract the single pinned daemon."""
import hashlib
import json
import os
from pathlib import Path
import tarfile
import tempfile
from urllib.request import Request, urlopen
from zipfile import ZipFile

def sha(stream, dest=None):
    digest = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        digest.update(block)
        if dest is not None:
            dest.write(block)
    return digest.hexdigest()

identity = json.loads(Path('input.json').read_text())
artifact = identity['checkpoint']
request = Request(f'https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/{artifact}/zip',
                  headers={'User-Agent':'btx-daemon-restore'})
request.add_unredirected_header('Authorization', 'Bearer ' + os.environ['GH_TOKEN'])
with tempfile.TemporaryFile() as data:
    with urlopen(request, timeout=45) as response:
        assert sha(response, data) == identity['outer_sha256']
    with ZipFile(data) as archive:
        manifest = json.loads(archive.read('manifest.json'))
        assert manifest['identity']['source'] == identity['source']
        assert manifest['identity']['target_build_complete']
        assert manifest['archive_sha256'] == identity['inner_sha256']
        with archive.open('build-state.tar.gz') as inner:
            assert sha(inner) == identity['inner_sha256']
        expected = {"btxd": identity["daemon_sha256"], "btx-cli": identity["cli_sha256"]}
        binary_dir = Path("runtime/bin")
        binary_dir.mkdir(parents=True)
        remaining = set(expected)
        prefix = "gui-pilot-runtime/qtbuild/bin/"
        with archive.open("build-state.tar.gz") as inner, tarfile.open(fileobj=inner, mode="r|gz") as build:
            for entry in build:
                name = entry.name.removeprefix(prefix)
                if not entry.name.startswith(prefix) or name not in remaining:
                    continue
                assert entry.isfile()
                path = binary_dir / name
                with path.open("xb") as output:
                    assert sha(build.extractfile(entry), output) == expected[name]
                path.chmod(0o700)
                remaining.remove(name)
                if not remaining:
                    break
        assert not remaining, remaining
Path("receipt/verified-inputs.json").write_text(json.dumps(identity, indent=2) + "\n")
