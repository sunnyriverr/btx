# Wallet label import recovery on Linux

Both focused patches were tested independently on release-0.34.16 at
`dac9aee5`. The original daemon fails the respective fixture.
Each focused candidate passes. Both fixtures also pass on the combined
candidate `e2891d29`.

| Check | Stock | Focused and combined candidates |
| --- | --- | --- |
| SQLite rejects the name write, including automatic rollback | Success with a live-only label | Wallet error, old label and purpose retained, identical retry persists |
| Input returns EIO after one valid JSONL record | Success and a durable prefix | Wallet error, both old labels survive reopen, identical retry persists both new labels |

[Save before/after CI](https://github.com/sunnyriverr/btx/actions/runs/42967279511) ·
[Read before/after CI](https://github.com/sunnyriverr/btx/actions/runs/42969038197) ·
[Combined CI](https://github.com/sunnyriverr/btx/actions/runs/42970543832) · [Provenance](provenance.json)

The fixtures use Python 3.12, the functional RPC client at the tested
checkout, and wallet-enabled Linux daemons. Run each against the appropriate
binary and SHA-256 from the provenance file.

```sh
python3 save_fixture.py --binary /path/to/btxd --functional-root /path/to/btx/test/functional --records save-records --expected-sha256 BINARY_SHA256
cc -Wall -Wextra -Werror -shared -fPIC read_fault.c -o read_fault.so -ldl
python3 read_fixture.py --binary /path/to/btxd --functional-root /path/to/btx/test/functional --records read-records --expected-sha256 BINARY_SHA256 --shim read_fault.so
```

Exit 1 records the stock regression, exit 0 a pass, and exit 2 an
inconclusive run. The CI jobs include the executed build and run entry
points. The daemon build reused verified cached objects. Scope is Ubuntu
22.04 with disposable SQLite regtest wallets and targeted faults. Native
Windows/macOS, legacy Berkeley DB, physical storage faults and the full
wallet suite were outside the runs.
