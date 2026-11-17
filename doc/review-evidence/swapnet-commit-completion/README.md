# Commitment replay recovery — Mac component evidence

**Fixed:** after an abrupt receive-side exit, a valid commit replay applies the saved agreement before acknowledgement. Completed commits remain deduplicated across reopen.

## Problem / repair

Stock records an inbox entry before applying a commit. Restart in that interval can ACK the original packet while the maker stays offered; the initiator can lock its original principal without settlement. The scoped fix adds a durable commit-completion receipt, foreign-key-bound to the existing 8,192-row inbox. Successful processing and receipt persistence precede ACK. Legacy seen-only rows undergo guarded replay; completed duplicates skip effects. Signature, expiry, mandate, budget and original-refund checks remain unchanged. Other packet kinds are not modified.

Code: ce5ddc904c9d817d5daff7951cbc032e67ce6ace, based on release-0.34.17 bd847e2b986722c1723b4cd60988d4f4908452d4. Exact product/test hashes are in qualification.json and MANIFEST.json.

## Executed evidence

Mac ARM64, Python 3.12.14, real production Application/Journal/Coordinator and SQLite. Actual fork-child exits at controlled admission, grant, session and pre-ACK boundaries; reopens reuse the same database and identity. Signed test packets use fixture identities. Chains, financial transactions/signing and transport callbacks are deterministic test doubles—not native funded BTX/BTC/EVM.

- Same final eight selected cases: **stock 5 fail / 3 pass → candidate 8 pass**. The five failures are assertions within this one defect/upgrade contract, not five bugs. One tests guarded revalidation of legacy already-applied state; stock's refund case stops at unapplied commitment. The earlier pilot separately proved stock refund survival.
- **20 unique regression cases qualified:**19 final passes plus one unchanged capacity/expiry case reused from the initial20-pass run. Same function AST and production hashes verified; zero skips on Mac.
- **Four existing recovery controls pass:** encrypted backup roundtrip, wrong-password/network/nonempty refusal, and two documented restore-tool cases on identical product bytes.
- Completed duplicates do not rerun handler effects after reopen. Legacy replay preserves exact pre-existing grant/reservation IDs and budget totals. Valid settlement has one funding per leg. With the maker deliberately withheld, original refund is refused before maturity and succeeds at maturity without a new funding, changed refund bytes or exposed secret.

[Stock log](baseline.log), [stock receipt](baseline-results.json), [final candidate log](candidate.log), [candidate receipt](candidate-results.json), [reused capacity receipt](initial-candidate-results.json), [initial test snapshot](initial-test.py), [restore log](restore.log), [restore receipt](restore-results.json), [code review](CODE-REVIEW.md), [evidence review](EVIDENCE-REVIEW.md), [qualification](qualification.json).

## Entry point and provenance

Maintained regression: `python3 -m pytest contrib/swapnet/tests/test_inbox_commit_recovery.py` on a checkout of ce5ddc904c9d817d5daff7951cbc032e67ce6ace with the repository's test dependencies. It imports existing test_runtime_recovery_v2 and test_execution_v2 fixtures; those files/attribution remain unchanged. The Mac-only abrupt-process cases require fork; they explicitly skip on Windows, so a Windows invocation is not equivalent evidence.

Actual local execution used isolated baseline/candidate package trees and the [runner](run_repair.py), with the bundled Python 3.12 and already-installed pure-Python pytest. Commands: `python3 -B run_repair.py baseline -k 'actual_exit or legacy_seen or caught_handler or original_refund'`, then `python3 -B run_repair.py candidate -k 'not receipts_share_capacity'`; [restore_controls.py](restore_controls.py) ran the four existing controls. Initial candidate evidence predates strengthened identity assertions, but has byte-identical product files and unchanged capacity-case AST. The full-checkout command is the maintained entry point; the separately assembled full-checkout reconstruction was not rerun just for packaging. Published logs/receipts redact local paths; MANIFEST hashes the published redacted bytes. Qualification also retains original local artifact hashes for provenance.

## Limits

No current native funded chains, native PQ signatures, embedded C++ worker, Linux/Windows, all packet kinds, full-suite or release qualification. No automatic reconstruction of old falsely ACKed messages whose sender already retired its packet: valid replay recovers; expired messages stay refused and the original refund is the fallback. Downgrading to an old binary retains the old behavior.

Independent code and evidence review found no remaining blocker. The evidence review caught count-versus-ID claims; relevant assertions were strengthened and requalified before delivery. This review was not a second native/platform execution.
