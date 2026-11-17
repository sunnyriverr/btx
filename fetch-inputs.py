"""Future hosted input verification only. Never executes retained product code."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import urllib.error
import urllib.request
import zipfile

ROOT = Path(os.environ['GITHUB_WORKSPACE'])
CONFIG = json.loads((ROOT / 'control/inputs.json').read_text())


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    require(str(ROOT.resolve()) == CONFIG['workspace'], 'Absolute workspace mismatch')
    require(shutil.disk_usage(ROOT).free >= CONFIG['limits']['initial_free_bytes'], 'Initial storage gate')
    memory_kib = next(int(x.split()[1]) for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemTotal:'))
    require(memory_kib * 1024 >= CONFIG['limits']['minimum_ram_bytes'], 'Host memory gate')
    records = ROOT / 'preflight-records'
    records.mkdir(exist_ok=True)
    destination = ROOT / 'saved-checkpoint'
    require(not destination.exists(), 'Refuse existing checkpoint directory')
    api = f"https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/{CONFIG['seed_artifact']}"
    headers = {'Authorization': 'Bearer ' + os.environ['GH_TOKEN'], 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
    with urllib.request.urlopen(urllib.request.Request(api, headers=headers), timeout=30) as response:
        metadata = json.load(response)
    require(metadata['id'] == CONFIG['seed_artifact'] and not metadata['expired'], 'Artifact unavailable')
    require(metadata['workflow_run']['id'] == CONFIG['seed_run'], 'Wrong producer run')
    require(metadata['workflow_run']['head_sha'] == CONFIG['seed_fixture'], 'Wrong producer commit')
    require(metadata['digest'] == 'sha256:' + CONFIG['seed_outer_sha256'], 'Artifact digest metadata changed')
    require(metadata['size_in_bytes'] == CONFIG['seed_outer_bytes'], 'Artifact length metadata changed')
    expiry = datetime.datetime.fromisoformat(metadata['expires_at'].replace('Z', '+00:00'))
    require(expiry > datetime.datetime.now(datetime.timezone.utc), 'Artifact expired')
    (records / 'seed-metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    # Keep authentication on api.github.com only. Fetch signed storage URL without it.
    request = urllib.request.Request(api + '/zip', headers=headers)
    try:
        urllib.request.build_opener(NoRedirect).open(request, timeout=30)
    except urllib.error.HTTPError as response:
        require(response.code == 302, 'Expected archive redirect')
        location = response.headers['Location']
    else:
        raise RuntimeError('Expected signed archive redirect')
    require(location.startswith('https://'), 'Non-HTTPS artifact storage')
    archive = ROOT / 'seed.zip'
    require(not archive.exists(), 'Refuse existing archive')
    received = 0
    with urllib.request.urlopen(location, timeout=30) as response, archive.open('xb') as f:
        while block := response.read(1024 * 1024):
            received += len(block)
            require(received <= CONFIG['seed_outer_bytes'], 'Oversized artifact')
            require(shutil.disk_usage(ROOT).free >= CONFIG['limits']['free_reserve_bytes'], 'Download reserve gate')
            f.write(block)
    require(received == CONFIG['seed_outer_bytes'] and digest(archive) == CONFIG['seed_outer_sha256'], 'Full artifact hash/length mismatch')
    destination.mkdir()
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        require(len(names) == 2 and set(names) == {'manifest.json', 'build-state.tar.gz'}, 'Unexpected artifact members')
        for name in names:
            item = z.getinfo(name)
            cap = CONFIG['limits']['manifest_bytes'] if name == 'manifest.json' else CONFIG['seed_outer_bytes']
            require(not item.is_dir() and item.file_size <= cap, 'Oversized ZIP member')
            require(not item.flag_bits & 1, 'Encrypted artifact member')
            # Read through ZipExtFile to check its CRC without trusting archive paths.
            with z.open(item) as source, (destination / name).open('xb') as target:
                count = 0
                while block := source.read(1024 * 1024):
                    count += len(block)
                    require(count <= cap, 'Expanded ZIP member exceeds bound')
                    target.write(block)
            require(count == item.file_size, 'ZIP member length mismatch')
    require(digest(destination / 'manifest.json') == CONFIG['seed_manifest_sha256'], 'Manifest hash mismatch')
    require(digest(destination / 'build-state.tar.gz') == CONFIG['seed_inner_sha256'], 'Inner archive hash mismatch')
    (records / 'input-verification.json').write_text(json.dumps({'status': 'VERIFIED', 'artifact': CONFIG['seed_artifact'], 'outer_sha256': digest(archive), 'manifest_sha256': digest(destination / 'manifest.json'), 'inner_sha256': digest(destination / 'build-state.tar.gz'), 'product_execution': False}, indent=2) + '\n')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        records = ROOT / 'preflight-records'
        records.mkdir(exist_ok=True)
        (records / 'input-failure.json').write_text(json.dumps({'status': 'INPUT_FAILURE', 'error_type': type(error).__name__, 'product_execution': False}) + '\n')
        raise
