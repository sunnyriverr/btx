# Original/draft P2MR transaction checks — actual result

Approved bounded Ubuntu24.04 x86_64 run43871315485 completed. Retained1e2btxd/btx-cli verified and hash-identical across both cases; no compilation/rebuild or product changes. Full artifact digest verified on download.

| Existing check | Original | Draft |
|---|---|---|
| Anti-fee-sniping locktime | PASS | PASS2.124s |
| Maximum-fee refusal | SetupFAIL: unsupportedbech32 RPC-8 | PASS48.811s, all startup/settxfee/setfeerate rows |
| Too-long mempool chain | Not reached | PASS24.486s,100ancestors with affordability/count/size assertions |
| Default transaction version2 | Not reached | PASS0.480s |
| setfeerate rounding/refusal/prior state | Not reached | PASS0.714s |

Draft method bodies total76.615s; this is not total job/setup runtime. Original fails on the intended unsupported-address setup; that is a fixture compatibility failure, not a product regression. Draft passes all five preserved contracts, with exact fee error codes/messages retained. No method skipped. The native result supports the test-only adaptation; it does not identify a new product defect or justify changes to wallet policy.

## Evidence and limits

Source1e2f8b5f; baseline and draft use btxd9b9ba0f8c993c4880c06b2bacbf448b71a8882a9beae461b030d557d81428583 and CLI5f0b5907cb70132b791b4941c4f0ed0d5a63c06f2613c3291e5bd6501bc9327d. Originalscriptc3e588e4...72c66b; draft78024d8b...8080b1; full hashes and per-method results in qualification-receipt.json. Draft file was not modified after execution.

Artifact14228192027 SHA256e6780b5855f2f4b128d7fc9ae6f1c52c0dce63c7da872349f81b4ac92337ec80 verified. See run-proposal/records/{comparison.json,original-methods.json,draft-methods.json,original-functional.log,draft-functional.log,verification-result.json}. Source/config/closure verification retained; no new payload/build claim beyond recorded run. JPP's prior unsupported-address observation and #774's chain recipe credited/reused; this execution qualifies the distinct full five-method script.

One paired Ubuntu run only. Harness-assisted direct BitcoinTestFramework: exact script bodies loaded with runpy, method completion observers, documented common initial CPU/offline/P2MR/policy profile. The original keeps original restart semantics; draft preserves shared profile across fee restarts. This is not an untouched standalone invocation, normal test_runner run or full-suite result. No Mac/Windows/release/mainnet/default MatMul qualification. No mutation campaign was run. Existing runner registration already names wallet_create_tx.py; no new runner entry needed, but that launcher route was not itself executed.

Both processes exited without timeout/resource stop. Owned groups verified absent and scratch/cache/data removed; sampled scratch peaks~22/26MiB. No real wallet/key files accessed. Only authorized fork workflow and sanitized records published; no upstream PR/comment. Session1SwapNet and Session2ModelNet execution separate. CIref reservation released after result; task/test ownership retained for local final review/delivery preparation.

Next: final source/evidence review and one clean test-only PR/handoff proposal with source compatibility and harness limits explicit. Recheck upstream head/author overlap before publication; user approval required. No repeat tests merely for a pending review. A normal-launcher check is a distinct remaining integration gate if needed for the intended maintainer decision, not an already-proven pass.
