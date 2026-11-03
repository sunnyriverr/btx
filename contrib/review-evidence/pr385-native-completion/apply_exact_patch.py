from pathlib import PurePosixPath
import re

def apply_patch(root, patch):
    """Apply only these exact unified text patches: no offsets, fuzz or Git writes."""
    lines = patch.read_text().splitlines(keepends=True)
    i = 0
    while i < len(lines):
        if not lines[i].startswith('--- a/'):
            raise ValueError('unexpected patch header: ' + lines[i])
        old = lines[i][6:].rstrip('\n'); i += 1
        if not lines[i].startswith('+++ b/'):
            raise ValueError('missing new-file header')
        new = lines[i][6:].rstrip('\n'); i += 1
        if old != new or PurePosixPath(new).is_absolute() or '..' in PurePosixPath(new).parts:
            raise ValueError('unsupported patch path')
        target = root / new
        source = target.read_text().splitlines(keepends=True)
        result = []; cursor = 0
        while i < len(lines) and not lines[i].startswith('--- a/'):
            match = re.fullmatch(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@[^\n]*\n?', lines[i])
            if not match:
                raise ValueError('unsupported hunk: ' + lines[i])
            start, count, new_start, new_count = [int(v) if v is not None else 1 for v in match.groups()]
            position = start - 1 if count else start
            if position < cursor:
                raise ValueError('overlapping hunks')
            result.extend(source[cursor:position]); cursor = position; i += 1
            consumed = emitted = 0
            while i < len(lines) and not lines[i].startswith(('@@ ', '--- a/')):
                line = lines[i]; i += 1
                if line[:1] not in (' ', '-', '+'):
                    raise ValueError('unsupported patch body')
                text = line[1:]
                if line[0] in (' ', '-'):
                    if cursor >= len(source) or source[cursor] != text:
                        raise ValueError('context mismatch in ' + new)
                    cursor += 1; consumed += 1
                if line[0] in (' ', '+'):
                    result.append(text); emitted += 1
            if consumed != count or emitted != new_count:
                raise ValueError('hunk length mismatch')
        result.extend(source[cursor:]); target.write_text(''.join(result))
