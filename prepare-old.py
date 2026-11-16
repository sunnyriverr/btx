"""Verify the previously inspected old package and this host's static closure."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import tarfile
import urllib.request

root = Path.cwd()
records = root / 'records'
archive = root / 'previous.tar.gz'
directory = root / 'previous-package'
package = directory / 'btx-0.34.16'
expected = {
    'bin/btxd': '62a4412f57b91f68484ad698e545715e96606f143a2854325ae9a7932f1d5b07',
    'bin/btx-cli': 'e3df2c1206939dc0c8bf9a1668e264518197bdeb60220baf43e5a0e26fa03c6c',
    'libexec/btxd.real': '8ee5f661b2cab4808d5e859bcf60771335b4dbea549c26f3407e2328f8bf292a',
    'libexec/btx-cli.real': '32b6687aedc8a498bddb078c2053024b8e35afa8b3d345072fd45b7cf689e032',
}
result = dict(binaries_executed=False, compiled=False, tests_run=False,
              source_association='Publisher claim074dac16; not independently reproduced')


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(2**20), b''):
            h.update(chunk)
    return h.hexdigest()


def read(args):
    return subprocess.check_output(args, text=True, timeout=30)


try:
    assert shutil.disk_usage(root).free > 8 * 2**30
    assert not directory.exists() and not archive.exists()
    with urllib.request.urlopen('https://github.com/btxchain/btx/releases/download/v0.34.16/btx-0.34.16-x86_64-linux-gnu.tar.gz', timeout=60) as response, archive.open('xb') as out:
        received = 0
        while chunk := response.read(2**20):
            received += len(chunk)
            assert received <= 99956587
            out.write(chunk)
    assert received == 99956587
    assert sha(archive) == '9bbfff065299b3d6e863ecdeb0e54917788c1c0395cfa1d2b61bc40bf364932b'
    directory.mkdir()
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
        assert len(members) <= 30000 and sum(m.size for m in members) <= 2 * 2**30
        assert all(not m.isdev() and not m.isfifo() for m in members)
        tar.extractall(directory, filter='data')
    for name, digest in expected.items():
        assert sha(package / name) == digest
    # Match the reviewed launcher's effective bundled-library search path, in a
    # clean child environment without an external glibc prefix or LD preload.
    libs = {}
    for line in read(['/sbin/ldconfig', '-p']).splitlines():
        match = re.match(r'\s*(\S+)\s+\(([^)]*)\)\s+=>\s+(\S+)', line)
        if match and 'x86-64' in match[2]:
            libs.setdefault(match[1], Path(match[3]))
    queue = [package / 'libexec/btxd.real', package / 'libexec/btx-cli.real']
    closure = {}
    version_tables = {}
    while queue:
        path = queue.pop(0).resolve()
        if str(path) in closure:
            continue
        header = read(['readelf', '-h', str(path)])
        assert 'Advanced Micro Devices X86-64' in header
        program = read(['readelf', '-l', str(path)])
        interpreter = re.search(r'Requesting program interpreter: ([^\]]+)', program)
        if interpreter:
            assert Path(interpreter[1]).is_file()
        dynamic = read(['readelf', '-d', str(path)])
        versions = read(['readelf', '-V', str(path)])
        runpaths = re.findall(r'\((?:RUNPATH|RPATH)\).*\[(.*?)\]', dynamic)
        resolved = {}
        for name in re.findall(r'\(NEEDED\).*\[(.*?)\]', dynamic):
            candidates = [package / 'lib' / name] + [
                Path(entry.replace('$ORIGIN', str(path.parent))) / name
                for group in runpaths for entry in group.split(':') if entry]
            provider = next((candidate for candidate in candidates if candidate.is_file()), libs.get(name))
            assert provider and provider.is_file(), (str(path), name)
            resolved[name] = str(provider.resolve())
            queue.append(provider)
        dependency = None
        needs = versions.split('Version needs section', 1)[1] if 'Version needs section' in versions else ''
        for line in needs.splitlines():
            match = re.search(r'File: (\S+)', line)
            if match:
                dependency = match[1]
            match = re.search(r'Name: (\S+)', line)
            if match and dependency:
                provider = resolved[dependency]
                if provider not in version_tables:
                    table = read(['readelf', '-V', provider])
                    definitions = table.split('Version definition section', 1)[1].split('Version needs section', 1)[0] if 'Version definition section' in table else ''
                    version_tables[provider] = set(re.findall(r'Name: (\S+)', definitions))
                assert match[1] in version_tables[provider], (str(path), dependency, match[1])
        closure[str(path)] = dict(sha256=sha(path), resolved=resolved, runpaths=runpaths)
    result.update(status='OLD_STATIC_CLOSURE_PASS', entrypoints=expected, closure=closure)
except BaseException as error:
    result.update(status='OLD_PREFLIGHT_FAILED', error=type(error).__name__ + ': ' + str(error))
    if directory.is_dir():
        shutil.rmtree(directory)
    raise
finally:
    archive.unlink(missing_ok=True)
    result.update(archive_removed=not archive.exists(), package_retained_for_test=directory.exists())
    (records / 'old-runtime-preflight.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'closure'}), flush=True)
