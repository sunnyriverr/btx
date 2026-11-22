# Verify the snapshot manifest before replacing the install

At `release-0.34.17` commit `7d65025bb3bff27e4f6c2fdc95f33e4b859a2df5`, a bad checksum for the advertised snapshot manifest stopped bootstrap only after the working installation had already changed. On Mac arm64 with Python 3.12, the [same driver](qualify.py) failed on the original and passed on the patch: the old launcher remained runnable at its original path with the same digest, and the identical archive installed B after restoring the correct manifest. See [before](before.json), [after](after.json), [baseline exit](before.log) and [candidate exit](after.log). Published output copies redact machine-local paths.

The [maintained regression failed on the original](regression-before.log). The [candidate suite](unit-after.log) passed 28 installer tests, and [the composed suite](unit-with-924.log) passed 29 with [#924](https://github.com/btxchain/btx/pull/924) applied. This patch is based directly on the release branch.

## Reconstruct the fixture

Place `qualify.py` alongside `source/` and `candidate/`. Each tree needs `contrib/faststart/btx-agent-setup.py`, `contrib/faststart/btx-faststart.py` and `test/util/btx_agent_setup_test.py` at the corresponding revision.

```sh
python3.12 qualify.py source before.json       # exits 1 on old-launcher preservation
python3.12 qualify.py candidate after.json   # exits 0
python3.12 -W 'ignore:Python 3.14 will, by default:DeprecationWarning' candidate/test/util/btx_agent_setup_test.py
```

The warning filter is limited to the existing Python 3.12 tar warning that otherwise affects strict stderr comparisons. The driver uses the real installer and checksum checks, fixture launchers, and a stub for the final bootstrap call. No real release install, daemon startup, snapshot load, Linux or Windows test.
