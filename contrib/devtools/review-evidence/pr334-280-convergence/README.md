# #334 + #280: one-key mirror convergence investigation

**Unresolved one-key shared-history recovery case; no production fix and no
Tested ACK for the full functional test.** AI-assisted work by Sunny River.

Source: base `cbf65894e6d61084527cd93e913a00c6794418dd`, production deltas from Jpp-matata's
#280 `da16864051e3f6a53bda6fc866293a5230965daf` and #334 `68a27f85ed64d05eed617eaf7ee72518afa9e99c`.
This branch's source tree reproduces those production deltas only, without
#340, #285/#331, private snapshot metadata or the PRs' new unit tests. Original
production authorship is Jpp-matata's; this is an integration/evidence record,
not a replacement fix or PR. The unchanged functional test is in its original
location; both diagnostic input changes are in this evidence directory.

## Observed results (one run per distinct scenario)

- Unchanged `feature_matmul_trusted_mirror_convergence.py`: fails at line550,
  `33 !=36`, without a candidate-set abort.
- Diagnostic copy skips only the two intermediate stranded-tip assertions in
  the large-gap case. It still fails the exact-target predicate after300s.
  Mirror holds winning36/37/38 bodies and an attestation each; tip36, headers48,
  no requests in flight. Logs repeat incomparable-quorum33/36 fail-closed.
- History control retains every original assertion but inserts7 shared blocks
  before the large-gap race. That scenario passes through exact authority/mirror
  tip55 and the relay-body checks. It then fails the separate deep-reorg refusal
  assertion. This is **not a full-test pass** or a new334-regression claim.
- A diagnostic logger pilot stopped on PythonDecimal serialization. Corrected
  withdefault=str, excluded from completion evidence; note retained.

The trace and control support recent signed twins remaining inside the six-block
window as the cause. #280's off-frontier filter requires threshold>=2; this
fixture is threshold1 and both signing nodes use the same key. Its retained
fail-closed policy refuses incomparable authority. This is not evidence that
ordinary mainnet2of3 mirrors fail. Mainnet1key requires an explicit override.

## Reproduce

Build btxd/btx-cli on this branch with normal repository instructions. Run the
unchanged test first using the generated test/config.ini and fresh datadirs.
Run diagnostic-convergence.py and history-control-convergence.py with
PYTHONPATH pointing to test/functional and the same generated config. Each
`invocation.json` records the exact run; paths are redacted. Normal CMake Release
build, macOS26.5.1/AppleM4,4real toy-regtestnodes, threshold1, legacy reorg policy,
checkblockindex1. Metal compiled but no device admission/full-Metal qualification
is claimed. No nativeLinux/Windows, restart, mainnet, default2of3, full-suite or
release qualification. No full285/331/fold run. Source/binary hashes in summary.

## Decision requested

Should the download scenarios use isolated signed history, or should this test
require automatic recovery after conflicting threshold1 history? Removing the
intermediate assertion alone hides a later stall. Aging history is a diagnostic
input control, not a production remedy. Please settle that authority expectation
before a product change or a test adjustment. The later finality assertion is
recorded separately and has not been attributed to334.

Detailed logs/patches/identities are below; no secret-bearing config, cookie,
wallet, chain datadir or binary is included.
