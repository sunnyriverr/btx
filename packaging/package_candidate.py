"""Future authorized package stage. Source prepared only; not executed locally.

The controller owns deadlines, process-group cancellation, capacity and retention.
run(argv, label, limit=seconds, cwd=None) must raise on failure and return stdout.
"""
from __future__ import annotations

import hashlib
import json
import os
import posixpath
import tarfile
import time
from pathlib import Path

SOURCE = '074dac167c26c1e091198f691ed5727817dba88a'
OLD_SOURCE = '88c9b49cb16360fc8fbf3f84003b8b54c29e6db5'
TREE = 'fc0957218a75f21f541077b76e953e80966595d9'
ATLAS = '0c2757a32e2540be6a2ed4810a915430cdb1cb7018a0ede75d9f4256910fa13f'
ARCHIVE = '7d9dab78797d6c4e9668d92d65fb909f218b256760e565345089a1bbbd724fc5'
OUTER = 'd7d146459d575f580a5ad5fa280e27c251c4c7756ed263acced281f868897318'
FIXTURE = '77f354f5bdeb9c5771083dfcd489de5f34f6d8cf'
TARGETS = ('btxd', 'btx-cli', 'btx-util', 'btx-tx', 'btx-wallet', 'btx-qt',
           'btx-guardd', 'btx-security', 'btx-native-qualify', 'btx-modeld',
           'btx-hcpd', 'btx-hosted', 'btx-open', 'btx-capability',
           'btx-capabilityd', 'btx-modelcheck', 'btx-matmul-backend-info')
COMPONENTS = (*TARGETS, 'btx-atlas')
HOST_RUNTIME_PACKAGES = ('libwebkit2gtk-4.1-0', 'libgtk-3-0',
                         'libayatana-appindicator3-1', 'librsvg2-2', 'libxdo3')


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path, tick=lambda: None):
    tick()
    with Path(path).open('rb') as stream:
        result = stream_sha(stream, tick)
    tick()
    return result


def stream_sha(stream, tick=lambda: None):
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
        tick()
        digest.update(chunk)
    tick()
    return digest.hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def elf(path):
    require(path.is_file() and not path.is_symlink(), f'Nonregular ELF input: {path}')
    with path.open('rb') as stream:
        header = stream.read(20)
    require(header[:6] == b'\x7fELF\x02\x01' and header[18:20] == b'\x3e\x00',
            f'Expected little-endian ELF64 x86_64: {path}')


def installed_versions(output):
    installed = {}
    for line in output.splitlines():
        fields = line.split('\t')
        require(len(fields) == 3, 'Unexpected dpkg package/version/status record')
        name, version, status = fields
        if status.endswith(' ok installed'):
            require(name not in installed and version, 'Duplicate or empty dpkg installed version')
            installed[name] = version
    require(installed, 'Empty installed package baseline')
    return installed


def archive_manifest(archive, tick=lambda: None):
    """Hash all file payloads without extraction, permitting ordered hardlinks.

    Symlinks are recorded as link text, never followed. Hardlinks must name an
    earlier regular member in this one root; tarfile then reads that payload.
    All member and link paths are checked before any extractfile call.
    """
    rows = {}
    tick()
    with tarfile.open(archive, 'r:gz') as handle:
        tick()
        members = []
        total = 0
        for m in handle:
            tick()
            members.append(m)
            require(len(members) <= 50000, 'Archive member cap')
            if m.isfile():
                total += m.size
            require(total <= 4 * 1024**3, 'Archive expanded byte cap')
        tick()
        seen, regular, links = set(), set(), set()
        for m in members:
            tick()
            name = m.name
            normalized = posixpath.normpath(name)
            require(name and not name.startswith('/') and normalized == name.rstrip('/')
                    and all(p not in ('', '.', '..') for p in name.rstrip('/').split('/')),
                    f'Unsafe member: {name}')
            require(normalized not in seen, f'Duplicate member: {name}')
            seen.add(normalized)
            require(normalized == 'btx-0.34.16' or normalized.startswith('btx-0.34.16/'),
                    f'Unexpected archive root: {name}')
            require(not (m.mode & 0o7000), f'Special mode: {name}')
            require(m.isfile() or m.isdir() or m.issym() or m.islnk(), f'Special member: {name}')
            if m.issym() or m.islnk():
                raw = m.linkname
                base = posixpath.dirname(normalized) if m.issym() else ''
                target = posixpath.normpath(posixpath.join(base, raw))
                require(raw and not raw.startswith('/') and
                        target.startswith('btx-0.34.16/'), f'Escaping link: {name}')
                # Reject ambiguous traversal through another symlink, even if
                # lexical normalization would appear bounded.
                require('..' not in raw.split('/'), f'Parent traversal link: {name}')
                if m.islnk():
                    require(target in regular, f'Hardlink must name earlier regular member: {name}')
                else:
                    links.add(normalized)
            if m.isfile():
                regular.add(normalized)
        for name in seen:
            tick()
            parts = name.split('/')
            require(not any('/'.join(parts[:i]) in links for i in range(1, len(parts))),
                    f'Member under symlink: {name}')
        for m in members:
            tick()
            name = m.name.rstrip('/')
            row = {'mode': oct(m.mode), 'size': m.size,
                   'type': 'file' if m.isfile() else 'directory' if m.isdir() else
                           'hardlink' if m.islnk() else 'symlink'}
            if m.isfile() or m.islnk():
                with handle.extractfile(m) as stream:
                    row['sha256'] = stream_sha(stream, tick)
            if m.issym() or m.islnk():
                row['target'] = m.linkname
                row['link_text_sha256'] = hashlib.sha256(m.linkname.encode()).hexdigest()
            rows[name.removeprefix('btx-0.34.16/')] = row
    tick()
    return rows


def package(w, inputs, python, run, records, tick=lambda: None) -> dict:
    package_started = time.monotonic()
    controller_tick = tick
    def tick():
        controller_tick()
        require(time.monotonic() - package_started <= 900,
                '15 minute package/probe total budget exhausted')
    raw_run = run
    def run(argv, label, limit=90, cwd=None):
        tick()
        output = raw_run(argv, label, limit=limit, cwd=cwd)
        tick()
        return output
    def digest(path):
        return sha(path, tick)
    tick()
    w, records = Path(w), Path(records)
    records.mkdir(parents=True, exist_ok=True)
    require(inputs['source'] == SOURCE and tuple(inputs['targets']) == TARGETS,
            'Source/17 target identity drift')
    require(str(w) == inputs['workspace'], 'Workspace identity drift')
    require(inputs['atlas_source'] == OLD_SOURCE and inputs['atlas_tree'] == TREE and
            inputs['atlas_archive_sha256'] == ARCHIVE and inputs['atlas_binary_sha256'] == ATLAS and
            inputs['atlas_artifact'] == 14040930895 and inputs['atlas_run'] == 43428864330 and
            inputs['atlas_fixture'] == FIXTURE,
            'Atlas input pin drift')
    require(Path(python).is_absolute() and Path(python).is_file(), 'Explicit selected Python required')
    # ABI/environment overrides cannot silently weaken current shipping gates.
    require(not any(k.startswith('BTX_RELEASE_') for k in os.environ), 'Release override environment')
    product = w / 'product'
    require(run(['git', 'rev-parse', 'HEAD'], 'package-source-head', limit=15,
                cwd=product).strip() == SOURCE, 'Accepted checkout head changed')
    require(not run(['git', 'status', '--porcelain', '--untracked-files=all'],
                    'package-source-status', limit=15, cwd=product).strip(), 'Dirty accepted checkout')
    require(run(['git', 'rev-parse', 'HEAD:gui/atlas'], 'package-atlas-tree',
                limit=15, cwd=product).strip() == TREE, 'Complete Atlas Git tree mismatch')
    require(not run(['git', 'status', '--porcelain', '--untracked-files=all', '--ignored', '--',
                     'gui/atlas'], 'package-atlas-status', limit=15, cwd=product).strip(),
            'Atlas working tree contains altered or extra inputs')
    atlas_dir = w / 'atlas-input'
    atlas = atlas_dir / 'btx-atlas.real'
    envelope_path = atlas_dir / 'provenance.json'
    receipt = json.loads(envelope_path.read_text())
    tick()
    provenance = receipt['verified_original_provenance']
    require(provenance['source'] == OLD_SOURCE and provenance['candidate_archive_sha256'] == ARCHIVE
            and provenance['candidate_files']['libexec/btx-atlas.real']['sha256'] == ATLAS,
            'Original Atlas producer provenance mismatch')
    # Fetcher receipt binds immutable provenance and ELF to the verified remote
    # artifact, producer run/head, complete outer ZIP and inner archive.
    expected = {'artifact_id': 14040930895, 'run_id': 43428864330,
                'producer_head_sha': FIXTURE, 'source_sha': OLD_SOURCE,
                'outer_sha256': OUTER, 'archive_sha256': ARCHIVE,
                'atlas_binary_sha256': ATLAS, 'atlas_tree_sha': TREE}
    require(all(receipt.get(k) == v for k, v in expected.items()), 'Atlas fetch verification receipt mismatch')
    elf(atlas)
    require(digest(atlas) == ATLAS, 'Atlas input ELF digest mismatch')
    bin_dir = w / 'gui-pilot-runtime/qtbuild/bin'
    before = {}
    for name in TARGETS:
        tick()
        path = bin_dir / name
        elf(path)
        before[name] = {'path': str(path), 'sha256': digest(path), 'source': SOURCE,
                        'origin': 'current-source C++ build in this controller run'}
    staged_atlas = bin_dir / 'btx-atlas'
    if os.path.lexists(staged_atlas):
        # A later explicitly repinned checkpoint may contain the prior package
        # attempt's unchanged input. Revalidate it; never accept arbitrary stale
        # files or silently overwrite a changed component.
        elf(staged_atlas)
        require(digest(staged_atlas) == ATLAS, 'Existing Atlas staging bytes differ')
    else:
        with atlas.open('rb') as source, staged_atlas.open('xb') as destination:
            for block in iter(lambda: source.read(1024 * 1024), b''):
                tick()
                destination.write(block)
    tick()
    (bin_dir / 'btx-atlas').chmod(0o755)
    before['btx-atlas'] = {'path': str(bin_dir / 'btx-atlas'), 'sha256': ATLAS,
                           'source': OLD_SOURCE, 'equivalent_atlas_tree': TREE,
                           'origin': 'reused source-equivalent component; not freshly compiled',
                           'producer': expected}
    write(records / 'package-inputs.json', before)
    start = package_started
    def bounded(argv, label, cap):
        remaining = 900 - (time.monotonic() - start)
        require(remaining > 1, '15 minute package/probe total budget exhausted')
        return run(argv, label, limit=min(cap, int(remaining)), cwd=w)
    # This is strictly a postcompile host-runtime preparation. Do not put it
    # in the compiler/configuration dependency setup: that baseline is fixed.
    query = ['dpkg-query', '-W', '-f=${binary:Package}\t${Version}\t${Status}\n']
    before_text = bounded(query, 'package-host-installed-before', 15)
    (records / 'package-host-installed-before.tsv').write_text(before_text)
    installed_before = installed_versions(before_text)
    try:
        bounded(['env', 'DEBIAN_FRONTEND=noninteractive', 'apt-get', 'install', '-y',
                 '--no-install-recommends', '--no-upgrade', *HOST_RUNTIME_PACKAGES],
                'package-host-runtime-install', 180)
    finally:
        # Also preserve a partial install's host changes before propagating
        # apt failure. The controller retains outer interruption/deadline logs.
        after_text = bounded(query, 'package-host-installed-after', 15)
        (records / 'package-host-installed-after.tsv').write_text(after_text)
        installed_after = installed_versions(after_text)
        changed = {name: {'before': version, 'after': installed_after.get(name)}
                   for name, version in installed_before.items()
                   if installed_after.get(name) != version}
        added = {name: version for name, version in installed_after.items()
                 if name not in installed_before}
        host_inputs = {'requested_packages': list(HOST_RUNTIME_PACKAGES),
                       'new_package_versions': added, 'changed_preexisting_packages': changed,
                       'before_inventory_sha256': digest(records / 'package-host-installed-before.tsv'),
                       'after_inventory_sha256': digest(records / 'package-host-installed-after.tsv'),
                       'scope': 'Postcompile packaging-host runtime inputs; not the compiled-input baseline. No apt update or upgrades requested.'}
        write(records / 'package-host-inputs.json', host_inputs)
    require(not changed, 'Runtime dependency install changed a preexisting package version or removed it')
    require(all(any(name.split(':', 1)[0] == requested for name in installed_after)
                for requested in HOST_RUNTIME_PACKAGES), 'Requested host runtime package missing')
    # Host GTK/WebKit is an explicit product dependency, not bundled by the Qt
    # helper. ldd only traces the verified ELF; no GUI or wallet is started.
    closure = bounded(['ldd', str(atlas)], 'package-atlas-host-closure', 30)
    require('not found' not in closure and '=>' in closure, 'Atlas host runtime closure unresolved')
    output = w / 'desktop-candidate'
    require(not output.exists(), 'Refuse stale package output directory')
    output.mkdir()
    scripts = product / 'scripts/release'
    bounded([str(python), str(scripts / 'package_release_archive.py'),
             '--version', '0.34.16', '--platform-id', 'linux-x86_64',
             '--archive-name', 'btx-linux-desktop-074-candidate.tar.gz',
             '--output-dir', str(output), '--source-root', str(product),
             '--python', str(python), '--btxd', str(bin_dir / 'btxd'),
             '--btx-cli', str(bin_dir / 'btx-cli'), '--btx-util', str(bin_dir / 'btx-util'),
             '--require-gui', '--require-model-helpers'], 'package-current', 600)
    archive = output / 'btx-linux-desktop-074-candidate.tar.gz'
    tick()
    manifest = archive_manifest(archive, tick)
    tick()
    for name in COMPONENTS:
        tick()
        require(manifest.get('bin/' + name, {}).get('type') == 'file', f'Missing wrapper: {name}')
        require(manifest.get('libexec/' + name + '.real', {}).get('type') in ('file', 'hardlink'),
                f'Missing real ELF component: {name}')
    guard = manifest.get('libexec/btx-guardd', {})
    require(guard.get('type') in ('file', 'hardlink') and guard.get('sha256') ==
            manifest['libexec/btx-guardd.real']['sha256'], 'Guard sibling payload mismatch')
    bounded([str(python), str(scripts / 'verify_release_btxd.py'), '--archive', str(archive),
             '--require-model-helpers', '--no-launch'], 'package-current-static-gate', 180)
    components = {name: {**before[name],
                        'staged_real_sha256': manifest['libexec/' + name + '.real']['sha256'],
                        'wrapper_sha256': manifest['bin/' + name]['sha256']}
                  for name in COMPONENTS}
    verdict = {'verdict': 'PACKAGE_STATIC_GATES_PASS_RUNTIME_QUALIFICATION_PENDING',
               'source': SOURCE, 'archive': str(archive), 'archive_sha256': digest(archive),
               'archive_bytes': archive.stat().st_size, 'components': components,
               'atlas_fetch_envelope_sha256': digest(envelope_path),
               'atlas_original_provenance': provenance,
               'package_host_inputs': host_inputs,
               'member_manifest': str(records / 'package-members.json'),
               'package_probe_seconds': time.monotonic() - start,
               'execution_disclosure': 'Current packager runs btxd -version and Python runtime/import probes. Standalone archive gate uses --no-launch. No wallet or GUI qualification.',
               'host_runtime_closure': 'Atlas GTK/WebKit and host display services required; verified builder ldd closure only. Archive is not sealed.',
               'qualification_pending': ['Ubuntu24.04 extracted-archive Qt and Atlas launch',
                                         'current daemon/service integration, restart and cleanup'],
               'shipping_gates': 'Unmodified current packager/verifier; all-ELF GLIBC2.38 and GLIBCXX/CXXABI/dependency gates; no overrides'}
    write(records / 'package-members.json', manifest)
    tick()
    write(records / 'package-provenance.json', verdict)
    tick()
    # Keep the candidate self-describing independently of the shorter-lived
    # checkpoint/log artifact, with original Atlas producer attribution intact.
    write(output / 'provenance.json', verdict)
    write(output / 'members.json', manifest)
    tick()
    return verdict
