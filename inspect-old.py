"""Bounded package inspection only: never launch an archive entry or a loader."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import tarfile
import time
import urllib.request

ROOT = Path.cwd()
RECORDS = ROOT / 'records'
ARCHIVE = ROOT / 'previous.tar.gz'
PACKAGE = ROOT / 'previous-package'
URL = 'https://github.com/btxchain/btx/releases/download/v0.34.16/btx-0.34.16-x86_64-linux-gnu.tar.gz'
DIGEST = '9bbfff065299b3d6e863ecdeb0e54917788c1c0395cfa1d2b61bc40bf364932b'
SIZE = 99956587
started = time.monotonic()
result = dict(tests_run=False, binaries_executed=False, compiled=False,
              archive_sha256=DIGEST, source_association='Publisher claim: 074dac16; not an independent build attestation')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


try:
    RECORDS.mkdir(exist_ok=True)
    assert shutil.disk_usage(ROOT).free > 8 * 2**30
    assert not ARCHIVE.exists() and not PACKAGE.exists()
    received = 0
    with urllib.request.urlopen(URL, timeout=60) as response, ARCHIVE.open('xb') as out:
        while chunk := response.read(1024 * 1024):
            received += len(chunk)
            assert received <= SIZE
            assert time.monotonic() - started < 300
            out.write(chunk)
    assert received == SIZE and digest(ARCHIVE) == DIGEST
    PACKAGE.mkdir()
    with tarfile.open(ARCHIVE) as archive:
        members = archive.getmembers()
        assert len(members) <= 30000
        assert sum(m.size for m in members) <= 2 * 2**30
        assert all(not m.isdev() and not m.isfifo() for m in members)
        archive.extractall(PACKAGE, filter='data')
    manifest = []
    launchers = []
    elf = []
    for path in sorted(PACKAGE.rglob('*')):
        if path.is_symlink() or not path.is_file():
            continue
        name = str(path.relative_to(PACKAGE))
        with path.open('rb') as f:
            magic = f.read(4)
        row = dict(path=name, bytes=path.stat().st_size, sha256=digest(path))
        manifest.append(row)
        if path.name in ('btxd', 'btx-cli') and path.parent.name == 'bin':
            assert row['bytes'] < 65536 and magic != b'\x7fELF'
            expected = {'btxd': '62a4412f57b91f68484ad698e545715e96606f143a2854325ae9a7932f1d5b07',
                        'btx-cli': 'e3df2c1206939dc0c8bf9a1668e264518197bdeb60220baf43e5a0e26fa03c6c'}
            assert row['sha256'] == expected[path.name]
            (RECORDS / (path.name + '.launcher.txt')).write_bytes(path.read_bytes())
            launchers.append(row)
        if magic == b'\x7fELF':
            sections = []
            for flag in ('-h', '-l', '-d', '-V'):
                sections.append(subprocess.check_output(['readelf', flag, str(path)],
                                                       text=True, timeout=30))
            # Readelf is static inspection, not ldd or dynamic-loader execution.
            report = '\n'.join(sections)
            row['elf_report'] = 'old-elf-' + row['sha256'] + '.txt'
            (RECORDS / row['elf_report']).write_text(report)
            elf.append(row)
        assert time.monotonic() - started < 480
    assert len(launchers) == 2 and elf
    (RECORDS / 'old-package-files.json').write_text(json.dumps(manifest, indent=2) + '\n')
    result.update(status='PACKAGE_STATIC_INVENTORY_PASS', launchers=launchers, elf=elf,
                  remaining='Review launcher-to-payload links, dependency/version closure and runtime profile before any BTX execution')
except BaseException as error:
    result.update(status='PREFLIGHT_FAILED', error=type(error).__name__ + ': ' + str(error))
    raise
finally:
    # This dedicated runner owns these exact paths; package contains no user wallet.
    if PACKAGE.is_dir():
        shutil.rmtree(PACKAGE)
    ARCHIVE.unlink(missing_ok=True)
    result.update(elapsed_seconds=round(time.monotonic() - started, 2),
                  package_removed=not PACKAGE.exists(), archive_removed=not ARCHIVE.exists())
    (RECORDS / 'old-package-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)
