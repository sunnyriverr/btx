"""Fetch one digest-pinned ELF; never build, restore a cache or launch it."""
import hashlib
import json
import os
from pathlib import Path
import urllib.parse
import urllib.request
import zipfile

PIN = json.loads((Path(__file__).resolve().parent / 'INPUTS.json').read_text())


class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, *args):
        result = super().redirect_request(request, *args)
        if result:
            assert result.full_url.startswith('https://')
            if urllib.parse.urlparse(result.full_url).netloc != 'api.github.com':
                result.remove_header('Authorization')
        return result


def main():
    root = Path(os.environ['RUNNER_TEMP']) / 'session3-atlas905-dialog-binary'
    root.mkdir(exist_ok=False)
    (Path(os.environ['RECORDS']) / 'binary-owned.json').write_text(json.dumps({'path': str(root)}) + '\n')
    archive = root / 'binary.zip'
    request = urllib.request.Request(
        'https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/' + str(PIN['binary_artifact']) + '/zip',
        headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'], 'User-Agent': 'BTX905 UI fixture'})
    with urllib.request.build_opener(Redirect).open(request, timeout=60) as response:
        data = response.read(PIN['ZIP_bytes'] + 1)
    assert len(data) == PIN['ZIP_bytes'] and hashlib.sha256(data).hexdigest() == PIN['ZIP_sha256']
    archive.write_bytes(data)
    with zipfile.ZipFile(archive) as z:
        assert z.namelist() == ['btx-atlas'] and z.getinfo('btx-atlas').file_size == PIN['binary_bytes']
        data = z.read('btx-atlas')
    assert hashlib.sha256(data).hexdigest() == PIN['binary_sha256']
    binary = root / 'btx-atlas'
    binary.write_bytes(data)
    binary.chmod(0o755)
    archive.unlink()
    print(json.dumps({'restored_binary_sha256': PIN['binary_sha256'], 'launched': False}))


if __name__ == '__main__':
    main()
