"""Offline evidence-data verifier. Does not import recipe code or execute BTX."""
from pathlib import Path
import hashlib
import json
import re
import sys
import zipfile


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / 'MANIFEST.json').read_text())
    actual = set()
    for path in root.rglob('*'):
        require(not path.is_symlink(), 'Unexpected symlink')
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
    wanted = set(manifest['files']) | {'MANIFEST.json', 'SHA256SUMS'}
    require(actual == wanted, 'Package file set differs from manifest')
    for name, item in manifest['files'].items():
        path = Path(name)
        require(not path.is_absolute() and '..' not in path.parts, 'Invalid manifest path')
        source = root / path
        require(source.stat().st_size == item['bytes'] and sha(source) == item['sha256'],
                'File digest/size mismatch: ' + name)
    sums = {}
    for line in (root / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ', 1)
        require(re.fullmatch('[0-9a-f]{64}', digest) is not None and name not in sums,
                'Invalid or duplicate checksum')
        sums[name] = digest
    require(set(sums) == actual - {'SHA256SUMS'}, 'Checksum file set differs')
    for name, digest in sums.items():
        require(sha(root / name) == digest, 'Checksum mismatch: ' + name)

    original_receipt = json.loads((root / 'evidence/qualification-receipt.json').read_text())
    for name, item in original_receipt['files'].items():
        path = root / 'evidence' / name
        require(path.stat().st_size == item['bytes'] and sha(path) == item['sha256'],
                'Original qualification receipt mismatch: ' + name)
    records = root / 'evidence/records14381370302/acceptance-records'
    parent = json.loads((records / 'result.json').read_text())
    gui = json.loads((records / 'gui/result.json').read_text())
    lifecycle = json.loads((records / 'lifecycle/result.json').read_text())
    require(parent['fixture_commit'] == '6d719e9191cea74a2e5ba7081e6beb02d7fd38bd', 'Wrong control')
    require(parent['archive_sha256'] == '915fae283089a325df65ef7521fffd6e30f5faa8d0bc8f2d77a2b6af52348a57', 'Wrong archive')
    require(parent['phases'] == dict.fromkeys(
        ['artifact', 'installed_tree', 'gui', 'lifecycle', 'unchanged_payload'], 'PASS'), 'Incomplete phases')
    for state in (parent, gui, lifecycle):
        require(state['overall'] == 'PASS' and not state['cleanup_signals']
                and not state['cleanup_remaining'] and state['runtime_removed'], 'Non-PASS or dirty cleanup')
    require(parent['payload_unchanged'] and gui['package_unchanged'], 'Changed installed payload')
    require(gui['qt_window_pass'] and gui['native_confirmation_checked']
            and gui['normal_shutdown_pass'], 'Incomplete GUI record')
    require(gui['rpc_control'] == {'chain': 'regtest', 'blocks': 0, 'peers': 0}, 'Wrong RPC profile')
    require(len(gui['connected_observations']) == 2, 'Missing connection observations')
    for row in gui['connected_observations']:
        require(all(text in row['text'] for text in ['LIVE LOCAL', 'regtest', '0 blocks']), 'Missing live observation')
    for value in gui.values():
        if isinstance(value, dict) and value.get('file', '').endswith('.png'):
            require(sha(records / 'gui' / value['file']) == value['sha256'], 'Screenshot mismatch')
    require(len(lifecycle['checks']) == 43 and all(x['pass'] for x in lifecycle['checks']), 'Lifecycle check failure')
    require(len(lifecycle['boots']) == 2 and all(
        len(x['health']) == 10 and all(y['pass'] for y in x['health']) for x in lifecycle['boots']), 'Missing health samples')
    require(lifecycle['package_before'] == lifecycle['package_after'], 'Changed lifecycle payload')
    require(lifecycle['boots'][0]['identities'] == lifecycle['boots'][1]['identities'], 'Identity changed')

    recipe = root / 'recipe'
    pins = json.loads((recipe / 'inputs.json').read_text())
    require(pins['artifact_id'] == 14319148652 and pins['producer_run'] == 44063898937, 'Wrong retained input')
    require(pins['source'] == parent['source'], 'Source mismatch')
    require(pins['archive_sha256'] == parent['archive_sha256'], 'Recipe archive mismatch')
    recipe_manifest = json.loads((recipe / 'payload-manifest.json').read_text())
    for name, item in recipe_manifest['files'].items():
        require(sha(recipe / name) == item['sha256']
                and (recipe / name).stat().st_size == item['bytes'], 'Recipe mismatch: ' + name)
    zip_path = root / 'evidence/records14381370302.zip'
    require(zip_path.stat().st_size == 708633 and sha(zip_path) ==
            '34645ac7a81a92a0c9ae1c595f66e948f1a7f89ed37d46f36377f479cc57bbff', 'Wrong raw evidence ZIP')
    with zipfile.ZipFile(zip_path) as archive:
        require(archive.testzip() is None and len(archive.namelist()) == 29, 'Raw ZIP CRC/count mismatch')
        for name in archive.namelist():
            require(hashlib.sha256(archive.read(name)).hexdigest() == sha(root / 'evidence/records14381370302' / name),
                    'Raw ZIP/extracted mismatch: ' + name)
    print('PASS: local package integrity and saved scoped results; no BTX or recipe code executed.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError, zipfile.BadZipFile) as error:
        print('FAIL: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
