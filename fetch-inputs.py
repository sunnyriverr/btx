"""Future runner-only bounded artifact IO; no product execution or bulk extraction."""
from pathlib import Path, PurePosixPath
import datetime
import hashlib
import json
import os
import shutil
import tarfile
import urllib.error
import urllib.request
import zipfile

W = Path(os.environ['GITHUB_WORKSPACE'])
C = json.loads((W / 'control/inputs.json').read_text())


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def artifact(prefix):
    artifact_id, run = C[prefix + '_artifact'], C[prefix + '_run']
    checksum, length = C[prefix + '_outer_sha256'], C[prefix + '_outer_bytes']
    api = f'https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/{artifact_id}'
    headers = {'Authorization': 'Bearer ' + os.environ['GH_TOKEN'], 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
    with urllib.request.urlopen(urllib.request.Request(api, headers=headers), timeout=30) as f:
        metadata = json.load(f)
    expiry = datetime.datetime.fromisoformat(metadata['expires_at'].replace('Z', '+00:00'))
    require(metadata['id'] == artifact_id and not metadata['expired'] and expiry > datetime.datetime.now(datetime.timezone.utc), 'Unavailable artifact')
    require(metadata['workflow_run']['id'] == run and metadata['workflow_run']['head_sha'] == C[prefix + '_fixture'], 'Artifact producer mismatch')
    require(metadata['digest'] == 'sha256:' + checksum and metadata['size_in_bytes'] == length, 'Artifact metadata mismatch')
    (W / 'build-records' / (prefix + '-artifact.json')).write_text(json.dumps(metadata, indent=2) + '\n')
    try:
        urllib.request.build_opener(NoRedirect).open(urllib.request.Request(api + '/zip', headers=headers), timeout=30)
    except urllib.error.HTTPError as response:
        require(response.code == 302, 'Expected signed artifact redirect')
        location = response.headers['Location']
    else:
        raise RuntimeError('Expected artifact redirect')
    require(location.startswith('https://'), 'Non-HTTPS artifact storage')
    path = W / (prefix + '-input.zip')
    count = 0
    # Authentication stays on api.github.com; signed storage receives no token.
    with urllib.request.urlopen(location, timeout=30) as source, path.open('xb') as target:
        while block := source.read(1024 * 1024):
            count += len(block)
            require(count <= length and shutil.disk_usage(W).free >= C['limits']['reserve_bytes'], 'Download bound')
            target.write(block)
    require(count == length and sha(path) == checksum, 'Complete artifact digest mismatch')
    return path


def member(z, name, destination, checksum, cap):
    matches = [x for x in z.infolist() if x.filename == name]
    require(len(matches) == 1 and not matches[0].is_dir() and not matches[0].flag_bits & 1, 'Missing/duplicate/encrypted member')
    info = matches[0]
    require(info.file_size <= cap, 'ZIP member bound')
    with z.open(info) as source, destination.open('xb') as target:
        count = 0
        while block := source.read(1024 * 1024):
            count += len(block)
            require(count <= cap and shutil.disk_usage(W).free >= C['limits']['reserve_bytes'], 'ZIP expansion bound')
            target.write(block)
    require(count == info.file_size and (checksum is None or sha(destination) == checksum), 'ZIP member digest mismatch')


def main():
    require(str(W.resolve()) == C['workspace'], 'Absolute workspace mismatch')
    require(shutil.disk_usage(W).free >= C['limits']['initial_free_bytes'], '16 GiB initial capacity')
    memory = next(x for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemTotal:'))
    require(int(memory.split()[1]) * 1024 >= C['limits']['minimum_ram_bytes'], '7 GiB memory admission')
    records = W / 'build-records'
    records.mkdir(exist_ok=True)
    for name in ['saved-checkpoint', 'historical', 'atlas-input']:
        (W / name).mkdir(exist_ok=False)
    checkpoint_zip = artifact('checkpoint')
    with zipfile.ZipFile(checkpoint_zip) as z:
        require(len(z.infolist()) <= 1000 and sum(x.file_size for x in z.infolist()) <= 256 * 1024**2, 'Checkpoint ZIP inventory bound')
        member(z, 'preflight-records/updated-checkpoint/manifest.json', W / 'saved-checkpoint/manifest.json', C['checkpoint_manifest_sha256'], 8 * 1024**2)
        member(z, 'preflight-records/updated-checkpoint/build-state.tar.gz', W / 'saved-checkpoint/build-state.tar.gz', C['checkpoint_inner_sha256'], 128 * 1024**2)
        for name, identity in C['historical'].items():
            require(name in ['result.json', 'dependencies-receipt.json', 'CMakeCache.txt', 'compile_commands.json', 'build.ninja'], 'Unexpected historical name')
            member(z, identity['zip_member'], W / 'historical' / name, identity['sha256'], identity['bytes'])
    previous = json.loads((W / 'historical/result.json').read_text())
    require(previous['verdict'] == 'PREFLIGHT_PASS' and previous['source'] == C['source'] and previous['planned_action_count'] == 3555, 'Unqualified checkpoint producer')
    atlas_zip = artifact('atlas')
    archive = W / 'atlas-input/original-candidate.tar.gz'
    provenance = W / 'atlas-input/original-provenance.json'
    with zipfile.ZipFile(atlas_zip) as z:
        require(set(z.namelist()) == {'btx-linux-gui-candidate.tar.gz', 'provenance.json'} and len(z.infolist()) == 2, 'Unexpected Atlas artifact members')
        member(z, 'btx-linux-gui-candidate.tar.gz', archive, C['atlas_archive_sha256'], C['atlas_archive_bytes'])
        member(z, 'provenance.json', provenance, None, 8 * 1024**2)
    original = json.loads(provenance.read_text())
    require(original['source'] == C['atlas_source'] and original['candidate_archive_sha256'] == C['atlas_archive_sha256'] and original['archive_size_bytes'] == C['atlas_archive_bytes'], 'Atlas provenance mismatch')
    require(original['candidate_files']['libexec/btx-atlas.real']['sha256'] == C['atlas_binary_sha256'], 'Atlas member provenance mismatch')
    found = False
    count = total = 0
    with tarfile.open(archive, 'r:gz') as tar:
        for info in tar:
            count += 1
            name = PurePosixPath(info.name)
            require(not name.is_absolute() and '..' not in name.parts and name.parts and name.parts[0] == 'btx-0.34.16', 'Atlas archive path')
            require(info.isfile() or info.isdir() or info.issym() or info.islnk(), 'Atlas archive special entry')
            total += info.size
            require(count <= 100000 and total <= 2 * 1024**3, 'Atlas archive inventory bound')
            if info.name != 'btx-0.34.16/libexec/btx-atlas.real':
                continue
            require(not found and info.isfile() and info.size <= 128 * 1024**2, 'Atlas must be a unique regular ELF input')
            found = True
            destination = W / 'atlas-input/btx-atlas.real'
            with tar.extractfile(info) as source, destination.open('xb') as target:
                shutil.copyfileobj(source, target, 1024 * 1024)
            require(sha(destination) == C['atlas_binary_sha256'], 'Atlas actual ELF digest mismatch')
            with destination.open('rb') as f:
                head = f.read(20)
            require(head[:6] == b'\x7fELF\x02\x01' and int.from_bytes(head[18:20], 'little') == 62, 'Atlas architecture mismatch')
            destination.chmod(0o755)
    require(found, 'Atlas ELF absent')
    envelope = {'artifact_id': C['atlas_artifact'], 'run_id': C['atlas_run'], 'producer_head_sha': C['atlas_fixture'], 'source_sha': C['atlas_source'], 'outer_sha256': C['atlas_outer_sha256'], 'archive_sha256': C['atlas_archive_sha256'], 'atlas_binary_sha256': C['atlas_binary_sha256'], 'atlas_tree_sha': C['atlas_tree'], 'verified_original_provenance': original}
    (W / 'atlas-input/provenance.json').write_text(json.dumps(envelope, indent=2) + '\n')
    (records / 'input-verification.json').write_text(json.dumps({'status': 'VERIFIED', 'source': C['source'], 'checkpoint_artifact': C['checkpoint_artifact'], 'checkpoint_manifest_sha256': C['checkpoint_manifest_sha256'], 'checkpoint_inner_sha256': C['checkpoint_inner_sha256'], 'atlas': envelope, 'BTX_execution': False}, indent=2) + '\n')
    # Large downloaded containers are redundant once selected byte-verified
    # inputs are retained; discard only this fresh job's own temporary files.
    checkpoint_zip.unlink()
    atlas_zip.unlink()
    archive.unlink()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        records = W / 'build-records'
        records.mkdir(exist_ok=True)
        (records / 'input-failure.json').write_text(json.dumps({'status': 'INPUT_FAILURE', 'error_type': type(error).__name__, 'BTX_execution': False}) + '\n')
        raise
