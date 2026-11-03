# Atlas workflow YAML correction

Fix: `6a0db2a0bc5a73dc2b553951889f1f3717758123`, based on Atlas `afd6591970e7f8d65871412b9d7cf03b48f30b97`.

The plain `run:` scalar contains `blocked:` and cannot parse as YAML. A literal block preserves the shell command and makes the definition valid. The code commit changes only `.github/workflows/atlas-native.yml` (one line replaced by two).

## Recorded local checks

macOS ARM64, Python 3.11.14, PyYAML and actionlint 1.7.12:

- Original YAML fails parsing at line 19; actionlint exits 1. Candidate YAML parses and actionlint exits 0.
- The complete parsed candidate equals a reference with only the offending original scalar quoted. No trigger, matrix, permission or command changes; the block adds a harmless trailing newline.
- `bash -n` passes. Original/candidate guard commands both return 1 with identical diagnostics without Cargo.lock, and 0 silently with it.
- Unchanged `atlas-source.yml` also passes actionlint. Its exact source is supplied here; `workflow-inventory.json` records both definitions checked.

`validation.json` is the original result; baseline/candidate YAML and validate.py are the exact executed files. Logs retain their original local relative filenames. `validator-provenance.json` records official release download URLs and SHA256s, verified against both release asset metadata and the checksum list before execution. No validator binary is included.

## Reproduce

Use Python 3 with PyYAML and a trusted actionlint 1.7.12 binary:

```sh
python3 validate.py --actionlint /path/to/actionlint
/path/to/actionlint -no-color -shellcheck= -pyflakes= atlas-source.yml
```

The script checks the expected baseline failure and candidate success, then the guard controls. It rewrites derived validation/log files in its directory. SHA256SUMS.json records the original supplied bytes. Optional external ShellCheck/Pyflakes analyses were disabled and are not claimed. Internal artifact review is not independent platform execution; preparation and checks used Codex.

## Limits and preserved evidence

This is local YAML/Actions-definition validation and a lock-file guard control, not a GitHub native job execution, compiler/dependency audit, runtime/installer test or release qualification. Existing successful owner check run 41651982533 and PR393 component run 41646082764 are unchanged; the earlier malformed-workflow runs 41651979574 and 41652802534 remain historical failures. No native acceptance tests were repeated for this formatting change.
