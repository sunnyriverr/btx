"""Future authorized package stage. Source prepared only; not executed locally.

The controller owns deadlines, process-group cancellation, capacity and retention.
run(argv, label, limit=seconds, cwd=None) must raise on failure and return stdout.
"""
from __future__ import annotations

import hashlib
import json
import os
import posixpath
import shutil
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
PACKAGING_PATCH = {
    'base_source': SOURCE,
    'relative_path': 'scripts/release/bundle_python_runtime.py',
    'original_sha256': '018d8dcbb0bfec2c36e62397b80dcad884b67422e0328409d189ba6cfb5aa2d4',
    'candidate_sha256': '721fa1f54b51223cde80a1c85c4b8c996da916c5dab2fd7ff4fc17a8be72eab7',
    'patch_sha256': '9ad1291bf4924465066c0f9ad11d06d823feaa6147a1f08a6c26859bc4795140',
}
COMPILED_CHECKPOINT = {
    'artifact': 14313303910,
    'outer_sha256': 'e51b4edf0724bbae7044a621c121e9c2437587f2c804c3637c86957af8549961',
    'inner_sha256': 'bbd94e974883ddde5f959a2c7347a7abff9cb5fa7440efcbb5a23a9509bba67e',
    'manifest_sha256': 'ac9302cc81c3f85d4253b77c8af43741eb4522bd6ee8063e512c7cefac1aeefb',
    'compile_pass': True,
    'run': 44047285383,
    'control': '42a4eab0b19f07fe9355060194dc1346bfc96abc',
    'source': SOURCE,
}
# Exact compiled input bytes retained in execution/checkpoint-summary.json.
# Current packager RUNPATH edits belong only in staged_real_sha256 below.
COMPILED_BINARY_SHA256 = {
    'btxd': '6ba61e63c2dde82e57f4e9f8817de2c6a251e32dd27cd2e13f96e0b40a03259f',
    'btx-cli': 'f6951a3073380cff1f878c417670498bce72af9d5466f89acabe8e7f873d1a0b',
    'btx-util': 'f4e5e8e9985b40a6ebf1cf3c4b89eb9785a0205b567e9af91f938396ebcbdd14',
    'btx-tx': '9504f57252e1a7b9fa758d812c54c59f501fdf32a9994ddda5c9988efd83eb01',
    'btx-wallet': 'e52ca0c77b12dbf50bcca346e112996787b6b52f5c712a3e795faf0f566e2fe9',
    'btx-qt': '1d8f37ec948cf02c472717152b4de47a3fd14020d961a76b37864bde967e941d',
    'btx-guardd': 'db638adace92887c6272af9a9143025245b225340b5db9727747c166bc2a0850',
    'btx-security': 'bd8c4f11a8056e2412331da8e8622e75eec57b02c2a9a9e072e516293f81c512',
    'btx-native-qualify': '26bee02f1c0008a1731af79870a0036938333af31bf2e9d9d6c5400b299c36c4',
    'btx-modeld': '1fd4691d5553f941d768cc588a65cedab7e4ff54ad22f57505ac8f1e73bb310c',
    'btx-hcpd': '73121a318c2914dbace7f2e07af6fd613a44f64f4dee381874d974eddf8b54a7',
    'btx-hosted': '1166225fd92925187f9400e90873da52fe8eafed48b1afd07326ecc493669561',
    'btx-open': '6dd5323ca44586917ac1652fe9a2b372ce5b3d593da8ac003af0c361c96dab49',
    'btx-capability': '854bccc070561f8526096c95d183a54dee2cb98057f8fb4d78f321be51faaa2b',
    'btx-capabilityd': 'ae426e757bcf80963810a270f72edceac00577ad4893a52513bd3aaec7a8778e',
    'btx-modelcheck': 'e1944c6c9e0c3b588f82b9e3b0672c1a90d113f28f504db11bde14356991f564',
    'btx-matmul-backend-info': '05975003b4c5c70cfc329832d92d78163fc78c82947b1452afe3588002050341',
}


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



def release_implementation_rows(root, tick):
    """Inventory regular release implementation inputs; Python caches are outputs."""
    require(root.is_dir() and not root.is_symlink(), 'Regular release implementation directory')
    rows = {}
    total = 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        tick()
        base = Path(directory)
        for name in dirs:
            require(not (base / name).is_symlink(), 'Release implementation directory symlink')
        dirs[:] = sorted(name for name in dirs if name != '__pycache__')
        for name in sorted(files):
            tick()
            path = base / name
            require(path.is_file() and not path.is_symlink(), 'Nonregular release implementation input')
            relative = path.relative_to(root).as_posix()
            require('__pycache__' not in Path(relative).parts, 'Unexpected Python cache input')
            size = path.stat().st_size
            total += size
            require(len(rows) < 128 and total <= 4 * 1024**2, 'Release implementation inventory bound')
            rows[relative] = {'bytes': size, 'mode': path.stat().st_mode & 0o777,
                              'sha256': sha(path, tick)}
    require(rows and 'bundle_python_runtime.py' in rows
            and 'package_release_archive.py' in rows and 'support_files.txt' in rows
            and 'verify_release_btxd.py' in rows and 'bundle_qt_gui.py' in rows,
            'Release implementation closure incomplete')
    return rows


def prepare_implementation(w, product, inputs, records, tick):
    patch = inputs['packaging_patch']
    require(all(patch.get(key) == value for key, value in PACKAGING_PATCH.items()),
            'Reviewed packaging patch identity drift')
    require(patch.get('scope') == 'Packaging implementation only; compiled product source and original object/binary bytes unchanged',
            'Packaging patch provenance scope')
    for name in ('portable_comparison_sha256', 'portable_evidence_review_sha256'):
        value = patch.get(name, '')
        require(isinstance(value, str) and len(value) == 64
                and all(c in '0123456789abcdef' for c in value), 'Portable evidence identity absent')
    patch_file = w / 'control/patch/nested-site-packages.patch'
    candidate = w / 'control/patch/bundle_python_runtime.py'
    for path, key in ((patch_file, 'patch_sha256'), (candidate, 'candidate_sha256')):
        require(path.is_file() and not path.is_symlink() and sha(path, tick) == PACKAGING_PATCH[key],
                'Reviewed packaging payload bytes changed')
    source = product / 'scripts/release'
    original_rows = release_implementation_rows(source, tick)
    require(original_rows['bundle_python_runtime.py']['sha256'] == PACKAGING_PATCH['original_sha256'],
            'Original bundler is not the reviewed baseline')
    overlay = w / 'package-overlay/scripts/release'
    require(not (w / 'package-overlay').exists(), 'Refuse stale packaging implementation overlay')
    overlay.mkdir(parents=True)
    for name in original_rows:
        tick()
        src, dst = source / name, overlay / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        # The closure has a strict four-MiB aggregate bound. Copy only regular
        # inputs, never links, preserving source executable/file modes.
        shutil.copy2(src, dst)
    shutil.copyfile(candidate, overlay / 'bundle_python_runtime.py')
    (overlay / 'bundle_python_runtime.py').chmod(original_rows['bundle_python_runtime.py']['mode'])
    overlay_rows = release_implementation_rows(overlay, tick)
    expected_rows = {name: dict(row) for name, row in original_rows.items()}
    expected_rows['bundle_python_runtime.py'].update(
        bytes=candidate.stat().st_size, sha256=PACKAGING_PATCH['candidate_sha256'])
    require(overlay_rows == expected_rows, 'Packaging overlay differs beyond the reviewed bundler delta')
    diagnostic = w / 'control/record-python-selection.py'
    require(diagnostic.is_file() and not diagnostic.is_symlink()
            and diagnostic.stat().st_size <= 64 * 1024, 'Regular bounded diagnostic source')
    value = {'scope': 'Compiled source074 unchanged; packaging implementation source074 plus one reviewed Python selector patch',
             'base_source': SOURCE, 'patch': dict(patch),
             'source_directory': str(source), 'overlay_directory': str(overlay),
             'source_files': original_rows, 'overlay_files': overlay_rows,
             'diagnostic_script': {'sha256': sha(diagnostic, tick),
                                   'bytes': diagnostic.stat().st_size,
                                   'control_path': str(diagnostic)},
             'source_integrity_after': 'PENDING', 'overlay_integrity_after': 'PENDING',
             'compile': 'No rebuild; original producer44047285383/artifact14313303910'}
    write(records / 'package-implementation.json', value)
    return overlay, value


def verify_implementation(w, product, overlay, value, records, tick):
    # Always run after a package/probe error as well as success. A mismatch
    # fails admission; it never replaces the original inputs or weakens a gate.
    value['source_integrity_after'] = 'CHECKING'
    value['overlay_integrity_after'] = 'CHECKING'
    write(records / 'package-implementation.json', value)
    try:
        require(release_implementation_rows(product / 'scripts/release', tick)
                == value['source_files'], 'Original release implementation changed')
        value['source_integrity_after'] = 'PASS'
        require(release_implementation_rows(overlay, tick) == value['overlay_files'],
                'Candidate packaging implementation changed during use')
        value['overlay_integrity_after'] = 'PASS'
        diagnostic = w / 'control/record-python-selection.py'
        require(diagnostic.is_file() and not diagnostic.is_symlink()
                and sha(diagnostic, tick) == value['diagnostic_script']['sha256'],
                'Selection diagnostic source changed during use')
        value['diagnostic_integrity_after'] = 'PASS'
    except BaseException as error:
        value['integrity_error'] = repr(error)
        raise
    finally:
        write(records / 'package-implementation.json', value)


def retain_packaging_evidence(w, overlay, output, implementation, tick):
    """Retain exact implementation delta outside the immutable shipping tar."""
    evidence = output / 'packaging-evidence'
    require(not evidence.exists(), 'Refuse stale candidate implementation evidence')
    evidence.mkdir()
    entries = {}
    files = [
        ('nested-site-packages.patch', w / 'control/patch/nested-site-packages.patch',
         PACKAGING_PATCH['patch_sha256']),
        ('bundle_python_runtime.py', overlay / 'bundle_python_runtime.py',
         PACKAGING_PATCH['candidate_sha256']),
        ('record-python-selection.py', w / 'control/record-python-selection.py',
         implementation['diagnostic_script']['sha256']),
    ]
    for name, source, digest in files:
        tick()
        require(source.is_file() and not source.is_symlink()
                and sha(source, tick) == digest, 'Candidate evidence source identity: ' + name)
        destination = evidence / name
        shutil.copy2(source, destination)
        require(destination.is_file() and not destination.is_symlink()
                and sha(destination, tick) == digest, 'Candidate evidence copy identity: ' + name)
        entries[name] = {'sha256': digest, 'bytes': destination.stat().st_size}
    value = {'scope': 'Packaging implementation delta and diagnostic source; outside shipping archive',
             'base_source': SOURCE, 'compiled_checkpoint': dict(COMPILED_CHECKPOINT),
             'files': entries}
    write(evidence / 'manifest.json', value)
    return value

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
    checkpoint_input_keys = {
        'checkpoint_artifact': 'artifact', 'checkpoint_run': 'run',
        'checkpoint_fixture': 'control', 'checkpoint_outer_sha256': 'outer_sha256',
        'checkpoint_inner_sha256': 'inner_sha256',
        'checkpoint_manifest_sha256': 'manifest_sha256',
        'checkpoint_compile_pass': 'compile_pass',
    }
    require(all(inputs[key] == COMPILED_CHECKPOINT[field]
                for key, field in checkpoint_input_keys.items()) and
            inputs['checkpoint_compile_pass'] is True and inputs['cpp_rebuild'] is False,
            'Compiled checkpoint identity/compile-pass drift')
    require(inputs['compiled_binary_sha256'] == COMPILED_BINARY_SHA256,
            'Compiled 17-target digest mapping drift')
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
        compiled_digest = digest(path)
        require(compiled_digest == COMPILED_BINARY_SHA256[name],
                f'Restored compiled input digest mismatch: {name}')
        before[name] = {'path': str(path), 'sha256': compiled_digest, 'source': SOURCE,
                        'origin': 'reused compiled checkpoint; not freshly built in this run',
                        'producer': dict(COMPILED_CHECKPOINT)}
    staged_atlas = bin_dir / 'btx-atlas'
    # This exact compiled checkpoint already contains the former attempt's
    # unchanged Atlas input. Require it instead of introducing new input bytes.
    elf(staged_atlas)
    require(digest(staged_atlas) == ATLAS, 'Restored Atlas staging bytes differ')
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
    overlay, implementation = prepare_implementation(w, product, inputs, records, tick)
    try:
        # This separate diagnostic records the selected interpreter's actual
        # module paths and both selectors before the unchanged shipping gates.
        # Failure is labelled separately, never reported as package admission.
        bounded([str(python), '-B', str(w / 'control/record-python-selection.py'),
                 '--workspace', str(w), '--python', str(python)],
                'package-python-selection', 60)
        selection_path = records / 'python-selection.json'
        selection = json.loads(selection_path.read_text())
        require(selection.get('status') == 'EXPECTED_NESTED_SELECTION_DELTA',
                'Actual interpreter selection diagnostic did not qualify the intended path')
        bounded([str(python), str(overlay / 'package_release_archive.py'),
                 '--version', '0.34.16', '--platform-id', 'linux-x86_64',
                 '--archive-name', 'btx-linux-desktop-074-candidate.tar.gz',
                 '--output-dir', str(output), '--source-root', str(product),
                 '--python', str(python), '--btxd', str(bin_dir / 'btxd'),
                 '--btx-cli', str(bin_dir / 'btx-cli'), '--btx-util', str(bin_dir / 'btx-util'),
                 '--require-gui', '--require-model-helpers'], 'package-current', 600)
    finally:
        verify_implementation(w, product, overlay, implementation, records, tick)
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
    retained_evidence = retain_packaging_evidence(w, overlay, output, implementation, tick)
    verdict = {'verdict': 'PACKAGE_STATIC_GATES_PASS_RUNTIME_QUALIFICATION_PENDING',
               'source': SOURCE, 'archive': str(archive), 'archive_sha256': digest(archive),
               'compiled_checkpoint': dict(COMPILED_CHECKPOINT),
               'compiled_binary_sha256': dict(COMPILED_BINARY_SHA256),
               'packaging_implementation': implementation,
               'packaging_implementation_sha256': digest(records / 'package-implementation.json'),
               'python_selection_sha256': digest(selection_path),
               'candidate_packaging_evidence': retained_evidence,
               'archive_bytes': archive.stat().st_size, 'components': components,
               'atlas_fetch_envelope_sha256': digest(envelope_path),
               'atlas_original_provenance': provenance,
               'package_host_inputs': host_inputs,
               'member_manifest': str(records / 'package-members.json'),
               'package_probe_seconds': time.monotonic() - start,
               'execution_disclosure': 'Base074 packager with reviewed nested-package selector runs btxd -version and Python runtime/import probes; prior explicit interpreter selection diagnostic. Original standalone archive gate uses --no-launch. No wallet or GUI qualification.',
               'host_runtime_closure': 'Atlas GTK/WebKit and host display services required; verified builder ldd closure only. Archive is not sealed.',
               'qualification_pending': ['Ubuntu24.04 extracted-archive Qt and Atlas launch',
                                         'current daemon/service integration, restart and cleanup'],
               'shipping_gates': 'Unmodified base074 packager/verifier and all shipping gates; only reviewed third-party Python selector differs in external overlay. All-ELF GLIBC2.38 and GLIBCXX/CXXABI/dependency gates; no overrides'}
    write(records / 'package-members.json', manifest)
    tick()
    write(records / 'package-provenance.json', verdict)
    tick()
    # Keep the candidate self-describing independently of the shorter-lived
    # checkpoint/log artifact, with original Atlas producer attribution intact.
    write(output / 'provenance.json', verdict)
    write(output / 'members.json', manifest)
    write(output / 'package-implementation.json', implementation)
    write(output / 'python-selection.json', selection)
    tick()
    return verdict
