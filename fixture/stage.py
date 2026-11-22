import hashlib
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

request = Request('https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/14730598159/zip',
                  headers={'User-Agent':'btx-fixture-stage'})
request.add_unredirected_header('Authorization', 'Bearer ' + os.environ['GH_TOKEN'])
with tempfile.TemporaryFile() as data:
    with urlopen(request, timeout=45) as response:
        assert sha(response, data) == '2e87d1c890a04058c7f0dd0b12e7b5e27cbb34173e1b6db1c564f000678a3633'
    with ZipFile(data) as archive:
        with archive.open('build-state.tar.gz') as inner:
            assert sha(inner) == '64e9cd620d4567fe291f3f4e65497798358d975798348aec9c364f2c5596cbb7'
        prefix = 'gui-pilot-runtime/qtbuild/bin/'
        expected = {
            prefix+'btxd': '4107e66f5122d69011337d342ebd30ff2eefdb4da3de75e6750fde099a750730',
            prefix+'btx-cli': '2db95cc3d8310876264eda6cfeed613173b7c8b60041db8e630b954e6af1a6b8',
        }
        with archive.open('build-state.tar.gz') as inner, tarfile.open(fileobj=inner, mode='r|gz') as build:
            for entry in build:
                if entry.name in expected:
                    assert entry.isfile()
                    with (Path('new') / Path(entry.name).name).open('xb') as output:
                        assert sha(build.extractfile(entry), output) == expected.pop(entry.name)
                    if not expected:
                        break
        assert not expected
