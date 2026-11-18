# Public confirmation recovery — macOS component evidence

**Fix:** repeating `confirmswap` after its first proposal-outbox insert fails now delivers the saved original proposal. It reuses #816's existing recovery helper rather than creating another intent or calling the financial coordinator tick.

Code: [`f6a6f179`](https://github.com/sunnyriverr/btx/commit/f6a6f1794dfb84f2d946fa7d8175ddd0cc3b3493), targeting `release-0.34.17@a97af7b3f379e33e3ec65db948468d875ade2841`. Its complete Git tree is identical to the locally tested `cbd42f14` tree; GitHub-created commit metadata differs. Exact file hashes, tree, environment, sanitization and setup notes: [manifest](manifest.json).

| Run | Result | Controller time |
| --- | --- | --- |
| Identical final confirmation module on untouched base | 12 failed / 11 passed | 4.553s |
| Same module with caller hook | 23 passed, zero skips | 4.869s |
| Existing #816 and market application modules | 36 passed, zero skips | 6.629s |

[Before log](baseline-final.log), [after log](candidate-qualified.log), [compatibility log](compatibility.log), [all case outcomes](checks.json). Baseline failures are missing delivery/expected refusals, not setup failures.

## What executed

macOS26.5.1 ARM64, retained Python3.12.10, pytest8.4.2, cryptography46.0.4. Actual production Application/Coordinator/Journal/SQLite Store/ForeignKeyVault and real Ed25519 envelope signatures, with simulated financial drivers/clocks and in-process transport.

The public offer→requester-bound quote→preview→confirmation path injects the same SQLite proposal-insert fault as #816. Same-process and Store/Vault reopened retries deliver the exact original proposal to the actual maker Application (`offered`). Original proposal/key/vault hashes and the one held10500/used0 reservation remain unchanged; no funding operations or chain transactions occur. Repeated enqueue/signing errors can recover on the same request.

Controls cover healthy/lost-preview-write retries, live queued/not-due/acknowledged deduplication without re-signing or sequence changes, expired-envelope and original-authority refusal, still-live authority after preview expiry, revocation, recovery conflicts, closed reservations and wrong principal/wallet. Seeded committed/funded/complete/refunded/cancelled states remain read-only and forbid tick/signing/driver calls. A live envelope may deduplicate after quote expiry; an expired envelope does not bypass authority checks. The public one-shot mandate co-expires with the quote here, so quote verification rejects first; the existing #816 module separately tests mandate expiry and original chain deadlines.

## Entry point

With Python3.12 and the repository's Python dependencies installed, the equivalent standard pytest selections are:

```sh
python3 -m pytest -q contrib/swapnet/tests/test_market_confirmation_recovery.py
python3 -m pytest -q contrib/swapnet/tests/test_initial_proposal_retry.py contrib/swapnet/tests/test_market_application.py
```

Our actual collector invoked the same pytest entry/arguments with a checksum-verified retained Python runtime, appended existing pure pytest dependencies, disabled plugin autoload and bounded each run to180s. It installed nothing and built no node. To reproduce before/after, place the unchanged new test file on a97 first, then apply the single caller hook. The first command must fail before and pass after; the compatibility selection passes with the candidate.

## Limits and reuse

Store/Vault reopening is not native process restart. No native wallet/node, funded BTX/Bitcoin/Ethereum, GUI, Linux/Windows, default-profile, full-suite or release qualification. Seeded progressed-state controls are not funded-chain proofs. No lost funds or duplicate funding were demonstrated. Existing native BTC/ETH results were not rerun or relabelled.

Built on Numair's public-market caller and #816's saved-proposal recovery, reusing the maintained initial-proposal snapshots/guards and execution-v2 fixtures. Internal diff/evidence review found no blocker; external review remains pending.

The first local Python3.9 attempt stopped during collection and is excluded. A provisional test incorrectly treated expired envelopes as deduplication candidates; the final test respects existing expiry/error precedence. Missing unrelated objects in the retained partial clone required an isolated sparse source checkout; the final product tree and two-file diff were verified unchanged when published. Public logs replace only personal absolute path prefixes. No databases, vaults, wallet data, credentials, binaries or runtime snapshots are included.
