# wallet_bumpfee OP_RETURN expectation

Two-line test correction for #630 at 8d6d8b1aabf371b12f2b1f5797b950fed7962d4e.
BTX rejects the first `data` output in `ParseOutputs`. The test now checks RPC
`-8` and the OP_RETURN prohibition for one data output alongside a payment
output. The duplicate-address assertion and valid replacement checks stay in
the test. The daemon needs no change.

A matched pair used the same retained wallet-enabled macOS arm64 binaries and
test framework, with two disposable regtest nodes, seed 630 and one
`connect=0` per node. The `no-filter` profile disabled Dandelion and fee-filter
messages. Regtest used economic MatMul validation and CPU diagnostic execution.

- [Original test](baseline.log) exited 1 at line 189. Its expected duplicate-key
  message did not match the daemon's OP_RETURN rejection.
- [Corrected test](candidate.log) exited 0 after the full file ran, including
  normal replacement outputs, watch-only PSBT, wallet restarts and fee checks.
- The earlier mempool timeout reported on #623 remains unexplained. Default
  Dandelion and other platforms were outside this paired run.

## Reconstruct the run

Use the pinned functional framework and test data with a config.ini from the
matching wallet build. Place `wallet_bumpfee.py`, `test_framework/`, `data/`,
`config.ini` and the supplied diagnostic wrapper in an isolated fixture with
matching `bin/btxd` and `bin/btx-cli`. Run
`python3 diagnose-single-connect.py baseline no-filter` on the original test.
Apply the [two-line patch](test-only.patch) in the source tree and replace only
the fixture's `wallet_bumpfee.py` with that patched copy. Run
`python3 diagnose-single-connect.py candidate no-filter` after the first
pair exits. The recorded candidate used the same wrapper with its test
filename pointed at the patched copy. The wrapper starts loopback regtest
nodes, leaves their datadirs for inspection, and requires free local ports.
Verify the binary and file hashes in the [receipt](receipt.json).

Thanks to repch1c for the original wallet test sweep in #623.
