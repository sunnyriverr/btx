# RPC fuzz-list lint matrix evidence

One-line CI integration of Jpp-matata's existing checker from [#680](https://github.com/btxchain/btx/pull/680), requested in his contributor catch-up. Base: `f40eb37a6fb8b665340fe92a2f248ff3f23ec7f6`. No checker, list classification or product-rule changes.

macOS arm64 / Bash3.2 / Python3.11.14: unchanged checker passes complete tracked scanner inputs (6213CPPfiles,552registered RPC names). All6216input Git blob identities matched again after restoration. Actual complete-source matrix entry point: baseline clean/missing/restored exits0/0/0; candidate0/1/0. The negative removes getblockcount and asserts its exact registered-but-neither diagnostic. Focused fixture additionally covers overlap, duplicates and unresolved definitions (12direct and12dispatcher executions). See complete-source-results.json, complete-dispatch-results.json and logs; source-inventory.json lists exact immutable input blobs.

Dependency bootstrap and25unrelated lint/test commands were bypassed. These checks qualify dispatch/failure propagation, not the full lint suite, runtime fuzz registration, native fuzz binary or other OSes. JPP's static checker retains its existing scan limitations; runtime fuzz registration remains authoritative. Expected failures are deliberately introduced controls. No current candidate-list defect is claimed.

## Reproduction

`python3.11 -B verify_dispatch.py` uses the bundled exact scripts plus a minimal tracked fixture and was executed at its packaged path. BTX_LINT_PYTHON may override the interpreter. `verify_complete.py` was also executed, against a retained complete-source snapshot. To reconstruct that snapshot, use an isolated Git repository populated with every CPPblob plus register.h/dispatcher/checker from source-inventory.json, track all listed paths and place it at complete-source; run `python3.11 -B verify_complete.py`. The complete snapshot is intentionally not duplicated in this evidence branch. Its source acquisition recipe is a reconstruction instruction, not an asserted fresh clone/build.

[Patch](rpc-fuzz-lint-matrix.patch), [complete paired results](complete-dispatch-results.json), [focused results](dispatch-results.json), [verification receipt](verification-receipt.json). Published receipts remove only local interpreter/root paths; counts/status remain unchanged. Review found no material issues; this is not external platform verification.
