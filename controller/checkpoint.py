"""Bounded, manifest-first checkpoint IO. Never use tar extractall."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import shutil
import stat
import tarfile

ROOTS = ('product', 'gui-pilot-runtime/qtbuild', 'gui-pilot-runtime/openssl')
MAX_BYTES = 4 * 1024**3
MAX_ENTRIES = 100000
RESERVE = 2 * 1024**3

def require(condition, message):
    if not condition:
        raise ValueError(message)

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()

def name_ok(name):
    p = PurePosixPath(name)
    require(isinstance(name, str) and str(p) == name and not p.is_absolute()
            and '..' not in p.parts and '.git' not in p.parts
            and '\\' not in name and '\x00' not in name, 'Unsafe path: ' + repr(name))
    require(any(name == root or name.startswith(root + '/') for root in ROOTS), 'Unapproved root')

def link_destination(name, target):
    require(isinstance(target, str) and target and not target.startswith('/')
            and '\\' not in target and '\x00' not in target, 'Unsafe link target')
    parts = list(PurePosixPath(name).parent.parts)
    for part in target.split('/'):
        if part in ('', '.'):
            continue
        if part == '..':
            require(parts, 'Escaping symlink')
            parts.pop()
        else:
            parts.append(part)
    result = '/'.join(parts)
    name_ok(result)
    return result

def validate_rows(rows):
    require(isinstance(rows, dict) and 0 < len(rows) <= MAX_ENTRIES, 'Entry bound')
    total = 0
    for name, row in rows.items():
        name_ok(name)
        require(row['kind'] in ('file', 'directory', 'link'), 'Special entry')
        require(type(row['mode']) is int and 0 <= row['mode'] <= 0o777, 'Permission bits')
        require(type(row['mtime_ns']) is int and 0 <= row['mtime_ns'] <= 2**63 - 1, 'Timestamp bound')
        if row['kind'] == 'file':
            require(type(row['bytes']) is int and 0 <= row['bytes'] <= MAX_BYTES, 'File bound')
            require(len(row['sha256']) == 64 and all(c in '0123456789abcdef' for c in row['sha256']), 'Digest syntax')
            total += row['bytes']
        if row['kind'] == 'link':
            link_destination(name, row['target'])
        # No traversal through a symlink, even if its eventual destination is allowed.
        for parent in PurePosixPath(name).parents:
            if str(parent) in rows:
                require(rows[str(parent)]['kind'] == 'directory', 'Non-directory ancestor')
        require(name in ROOTS or str(PurePosixPath(name).parent) in rows, 'Missing parent')
    require(total <= MAX_BYTES, 'Live byte bound')
    # Resolve symlink chains with POSIX component ordering. Lexical normalization
    # alone misses a/../b when a itself redirects to a different allowed root.
    for name, row in rows.items():
        if row['kind'] != 'link':
            continue
        pending = list(PurePosixPath(name).parent.parts) + row['target'].split('/')
        resolved = []
        links = 0
        while pending:
            part = pending.pop(0)
            if part in ('', '.'):
                continue
            if part == '..':
                require(resolved, 'Symlink chain escapes workspace')
                resolved.pop()
                continue
            resolved.append(part)
            destination = '/'.join(resolved)
            entry = rows.get(destination)
            if entry and entry['kind'] == 'link':
                links += 1
                require(links <= 40, 'Symlink cycle/depth')
                resolved.pop()
                pending = entry['target'].split('/') + pending
        name_ok('/'.join(resolved))
    return total

def verify_archive(archive, manifest, tick=lambda: None):
    rows = manifest['rows']
    validate_rows(rows)
    require(sha(archive) == manifest['archive_sha256'], 'Archive digest')
    seen = set()
    with tarfile.open(archive, 'r:gz') as stream:
        for member in stream:
            tick()
            name = member.name
            name_ok(name)
            require(name not in seen and name in rows, 'Duplicate/unlisted member')
            seen.add(name)
            require(len(seen) <= MAX_ENTRIES, 'Archive entry bound')
            row = rows[name]
            kind = 'file' if member.isfile() else 'directory' if member.isdir() else 'link' if member.issym() else 'forbidden'
            require(kind == row['kind'], 'Member type/hardlink mismatch')
            require(member.mode == row['mode'], 'Member mode mismatch')
            if kind == 'file':
                require(member.size == row['bytes'], 'Member size')
                h = hashlib.sha256()
                file = stream.extractfile(member)
                for block in iter(lambda: file.read(1024**2), b''):
                    tick()
                    h.update(block)
                require(h.hexdigest() == row['sha256'], 'Member digest')
            elif kind == 'link':
                require(member.linkname == row['target'], 'Link mismatch')
    require(seen == set(rows), 'Missing members')

def restore(workspace, archive, manifest, tick=lambda: None):
    verify_archive(archive, manifest, tick)
    for root in ROOTS:
        require(not os.path.lexists(workspace / root), 'Restore root already exists')
    rows = manifest['rows']
    for name in sorted(rows, key=lambda n: len(PurePosixPath(n).parts)):
        if rows[name]['kind'] == 'directory':
            (workspace / name).mkdir(parents=True, exist_ok=False)
    with tarfile.open(archive, 'r:gz') as stream:
        for member in stream:
            tick()
            row = rows[member.name]
            path = workspace / member.name
            if row['kind'] == 'file':
                with path.open('xb') as out, stream.extractfile(member) as source:
                    shutil.copyfileobj(source, out, 1024**2)
            elif row['kind'] == 'link':
                path.symlink_to(row['target'])
    for name in sorted(rows, key=lambda n: len(PurePosixPath(n).parts), reverse=True):
        row = rows[name]
        if row['kind'] != 'link':
            os.chmod(workspace / name, row['mode'])
        os.utime(workspace / name, ns=(row['mtime_ns'], row['mtime_ns']), follow_symlinks=False)
    require(snapshot(workspace, tick) == rows, 'Restored snapshot mismatch')

def snapshot(workspace, tick=lambda: None):
    rows = {}
    def walk(path):
        tick()
        name = path.relative_to(workspace).as_posix()
        if '.git' in PurePosixPath(name).parts:
            return
        st = path.lstat()
        row = {'mode': stat.S_IMODE(st.st_mode), 'mtime_ns': st.st_mtime_ns}
        if stat.S_ISLNK(st.st_mode):
            row.update(kind='link', target=os.readlink(path))
        elif stat.S_ISREG(st.st_mode):
            require(st.st_nlink == 1, 'Hardlinked file')
            row.update(kind='file', bytes=st.st_size, sha256=sha(path))
        elif stat.S_ISDIR(st.st_mode):
            row['kind'] = 'directory'
        else:
            raise ValueError('Special file')
        rows[name] = row
        require(len(rows) <= MAX_ENTRIES, 'Snapshot entry bound')
        if row['kind'] == 'directory':
            for child in sorted(path.iterdir()):
                walk(child)
    for root in ROOTS:
        if (workspace / root).exists():
            walk(workspace / root)
    validate_rows(rows)
    return rows

def create(workspace, output, identity, tick=lambda: None):
    before = snapshot(workspace, tick)
    total = validate_rows(before)
    require(shutil.disk_usage(workspace).free >= total + RESERVE + 512 * 1024**2, 'Checkpoint headroom')
    output.mkdir(exist_ok=False)
    archive = output / 'build-state.tar.gz'
    with tarfile.open(archive, 'w:gz', compresslevel=1, format=tarfile.PAX_FORMAT) as stream:
        for name in sorted(before):
            tick()
            stream.add(workspace / name, arcname=name, recursive=False)
    require(snapshot(workspace, tick) == before, 'Tree changed during checkpoint')
    manifest = {'workspace': str(workspace), 'identity': identity, 'rows': before, 'archive_sha256': sha(archive)}
    verify_archive(archive, manifest, tick)
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest
