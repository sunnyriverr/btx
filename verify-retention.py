"""Future post-upload metadata readback. This does not re-download archive bytes."""
import json
import os
import urllib.request

artifact = int(os.environ['ARTIFACT_ID'])
digest = os.environ['ARTIFACT_DIGEST'].removeprefix('sha256:')
if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
    raise RuntimeError('Invalid upload digest')
request = urllib.request.Request(
    f'https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/{artifact}',
    headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'], 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'},
)
with urllib.request.urlopen(request, timeout=30) as response:
    metadata = json.load(response)
expected_name = f"session3-linux-desktop-preflight-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
if not (metadata['id'] == artifact and metadata['name'] == expected_name and not metadata['expired']
        and metadata['workflow_run']['id'] == int(os.environ['GITHUB_RUN_ID'])
        and metadata['digest'] == 'sha256:' + digest and metadata['size_in_bytes'] > 0):
    raise RuntimeError('Uploaded artifact readback mismatch')
print(json.dumps({'status': 'RETENTION_METADATA_VERIFIED', 'artifact': artifact, 'sha256': digest, 'bytes': metadata['size_in_bytes'], 'run': metadata['workflow_run']['id'], 'full_archive_redownloaded': False}))
