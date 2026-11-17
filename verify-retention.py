"""Future post-upload readback only; full downloaded-byte verification is later."""
import json
import os
import urllib.request

for kind in ['records', 'candidate']:
    value = os.environ.get(kind.upper() + '_ID', '')
    if not value:
        if kind == 'records':
            raise RuntimeError('Records upload identity absent')
        continue
    artifact_id = int(value)
    digest = os.environ[kind.upper() + '_DIGEST'].removeprefix('sha256:')
    if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise RuntimeError('Invalid upload digest')
    request = urllib.request.Request(f'https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/{artifact_id}', headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'], 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=20) as response:
        actual = json.load(response)
    expected = f"session3-linux-desktop-{'package-records' if kind == 'records' else 'package-candidate'}-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    if not (actual['id'] == artifact_id and actual['name'] == expected and actual['workflow_run']['id'] == int(os.environ['GITHUB_RUN_ID']) and actual['digest'] == 'sha256:' + digest and actual['size_in_bytes'] > 0 and not actual['expired']):
        raise RuntimeError('Uploaded artifact identity mismatch')
    print(json.dumps({'status': 'UPLOAD_METADATA_VERIFIED', 'kind': kind, 'id': artifact_id, 'sha256': digest, 'bytes': actual['size_in_bytes'], 'full_redownload': False}))
