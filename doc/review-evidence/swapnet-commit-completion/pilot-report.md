# Valid commit interruption / replay pilot

**REPRODUCED: replay falsely acknowledges an unapplied commit after abrupt receiver exit. Original refund remains available at maturity in the deterministic ledger fixture.** Product code unchanged; no posting. Three focused cases passed, including the test that establishes the current defect.

## Exact execution

Mac ARM64, Python3.12.14. Reused existing pure-Python pytest installation from user site (not a Python3.9 execution). Production Application/Journal/Coordinator from release-0.34.17 bd847e2b986722c1723b4cd60988d4f4908452d4; loaded paths/hashes in pilot-receipt.json. Current branch was rechecked unchanged before execution.

Command: bundled Python3.12 `-B run_pilot.py`; existing runtime-recovery `apps` fixture plus existing deterministic Identity/Ledger/Driver reused. No rebuild, native daemon, actual chain funding or new dependencies. `PYTHONDONTWRITEBYTECODE=1`, plugin autoload/cache disabled. The actual pytest run finished in0.55s, inside the20-minute pilot bound.

## Discriminating observation

Reach an ordinary authenticated signed commit through real Application wire validation and owner-created mandates/market/quote acceptance. Maker is offered; initiator's original commit is durably queued. Close the original maker Store, fork one child which opens the same Application/SQLite with the same identity, and call its ordinary on_message. Wrap only journal.seen: call the unmodified durable implementation, assert new receipt, then `os._exit(73)` before returning to the handler. The parent joins the exited child and opens a new receiver on the same database. This is an actual abrupt child-process exit at the selected deterministic cut, not a clean daemon stop or a native btxd SIGKILL test.

On replaying identical valid original bytes:
- committed inbox marker survives;
- receive_commit does not run: maker stays **offered**, with zero grant rows for this swap;
- an ACK for the exact original message id is enqueued and delivered;
- sender's original outbox row becomes acknowledged;
- initiator has **one** original long-leg funding; maker has **zero** short-leg funding after8 normal steps. A later funded reference does not repair offered→committed.

The observed impact is failed settlement and temporary original-principal lock, with normal funding/refund fees. It does not prove theft, double funding, permanent loss or weakened refund safety.

## Refund and legitimate controls

One block before original long-leg maturity, the original output remains locked. At original maturity the existing coordinator refunds that original funding; after confirmations it reports refunded. Serialized original funding bytes remain identical; no second funding, no counterparty funding, no exposed preimage. Test clocks/heights were advanced explicitly; the wait was not measured on a public/native chain.

Healthy valid delivery plus duplicate of an already-processed commit completes both legs, exactly one funding each and no extra grant. A normal caught handler error removes the inbox marker; healthy replay commits and settles both legs, exactly one funding each. These distinguish the abrupt-exit persistence gap from ordinary exceptions and legitimate deduplication.

## Limits and setup

Real Application/Journal/Store/SQLite and signed packet validation with fixture Ed25519 identities; deterministic chain, keys, funding/refund/signing and transport callbacks are simulated. No native BTX/BTC/EVM, native PQ keys, C++ worker lifecycle, release or full-suite qualification. Single focused run/one injected cut; no failure-frequency or all-handler result claimed.

Two launcher errors occurred before test collection: pytest was absent from the bundled runtime, then a reporter hook used an incorrect parameter name. Reused the earlier runner's installed pytest location and corrected only the reporter signature. Neither is a product failure or qualification result. No passing case was repeated. Learnings: reuse the existing runner template with its dependencies/hook signatures, as well as its product fixture.

Storage preflight fell below1.25GiB reserve. Historical completed-task read-only GitHub JSON snapshots were losslessly gzip archived and roundtrip SHA verified; see storage-archive-receipt*.json for every original path, compressed replacement, exact hash and restore command. No wallet, binary, build object, production or active peer file was removed. The fixture started after reserve recovered. No child/runtime remains alive; fixture Stores closed on teardown. Small disposable fixture databases retained locally for audit, not shared.

## Next decision

Scope a receive-side completion/processing marker repair across affected handlers, preserving legitimate replay, signature/expiry validation and no duplicate effects. Do not hold network/signing work in a SQL transaction by default. Need design/implementation authorization before changes; no fix or publication yet. No further native matrix work merely to broaden coverage.

Evidence: [harness](test_inbox_restart.py), [runner](run_pilot.py), [log](pilot.log), [results](pilot-results.jsonl), [source/execution receipt](pilot-receipt.json), [independent audit](PILOT-REVIEW.md).
