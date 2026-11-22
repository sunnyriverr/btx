# Failed forced installer replacement

At `release-0.34.17` commit `7d65025bb3bff27e4f6c2fdc95f33e4b859a2df5`, a simulated disk write error after archive verification left the original launcher missing. With the proposed patch, the same launcher remained runnable at the original path with an identical SHA-256. The same replacement archive installed successfully on retry in both cases. No-force refusal, the separate data sentinel and staging cleanup passed.

The [same driver](qualify.py) ran on macOS arm64 with Python 3.12 against the original and patched installer. It invoked the real setup entry point with temporary local manifests, archive hashes and executable shell launchers. It injected `ENOSPC` on the second staging write in the verified replacement tar archive. See [before](before.json), [after](after.json), [expected baseline failure](before.log) and [candidate output](after.log). The archive SHA-256 is identical in both receipts. Machine-local path prefixes were redacted in the copied outputs.

The new maintained case covers extraction and promotion errors. Both cases lost the previous launcher on the original installer, and both passed on the candidate. The full installer unit file passed 27 tests on the original and 28 on the candidate. See the [new test on the original](regression-before.log), [original suite](unit-before.log) and [candidate suite](unit-after.log).

## Reconstruct the layout

Place `qualify.py` alongside `source/` and `candidate/`. Each directory contains `contrib/faststart/btx-agent-setup.py` and `test/util/btx_agent_setup_test.py` at the corresponding revision. For the full installer unit suite also keep the unchanged `contrib/faststart/btx-faststart.py` sibling.

```sh
python3.12 qualify.py source before.json       # exit 1 at the launcher assertion
python3.12 qualify.py candidate after.json   # exit 0
python3.12 -W 'ignore:Python 3.14 will, by default:DeprecationWarning' candidate/test/util/btx_agent_setup_test.py
```

The warning filter is limited to Python 3.12's existing tar deprecation message, which otherwise affects strict stderr comparisons. The run used fixture launchers and injected errors. It did not exercise actual disk exhaustion, process interruption, concurrent installs, release binaries, daemon startup, Linux or Windows.
