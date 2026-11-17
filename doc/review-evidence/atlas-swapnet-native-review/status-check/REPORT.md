# Atlas SwapNet status observations — bounded check complete

**No product defect found. Eleven focused checks pass, zero skips**, on release-0.34.17 `cd3078e76398b20b7f500acd1348a5b5455f3d5e`, macOS26.5.1 ARM64 / Node24.13.0. Actual `swapnetView`, its transitive production modules and the existing upstream `dom-stub.mjs` were used. Bridge replies/rejections and their payloads were controlled, not obtained from a native Atlas window or live RPC. No product patch, build, wallet, UI automation or upstream publication.

## Existing coverage and the actual gap

Reviewed all26 files listed in current gui/atlas/tests. None references these six RPC names or imports the SwapNet page. Generic observe.test.mjs covers title fallback, shape/row bounds and shared metrics, not this page. browser_smoke.py's workspace list omits swapnet. Existing native Rust `directory_and_swap_reads` explicitly asserts getswapnetworkinfo/getswapvalidationinfo and refuses reviewed operations; all six status methods are present in the source read allowlist. This is source inspection, not another Rust execution. Current RPC classification/commands/contract tests and swapnet.js are byte-identical to our prior source admission, so no need to repeat generic approval work. Numair's209webtests and template-check report is attributed prior evidence, not a test we ran here.

| Method | Existing direct page test | New exact-record and isolated-error checks |
|---|---|---|
| getswapnetworkinfo | None found | PASS |
| getswapbootstrapinfo | None found | PASS |
| getswapvalidationinfo | None found | PASS |
| getswaphealth | None found | PASS |
| listswapassets | None found | PASS |
| getswapcapabilities | None found | PASS |

## What the eleven checks prove

- All six wrapped responses reach their own exact serialized records, in the expected read order, with empty parameters. No prepare/execute/cancel calls occur from loading or refreshing status.
- Bare responses also preserve waiting-for-peer, missing-wallet, locked-asset, worker-error and false capability fields; they are not replaced by invented healthy metrics.
- Each method's rejected read is independently exercised: its warning remains explicit and the other five records survive.
- All-six unavailability produces six warnings and no successful records.
- Healthy → failed health read → healthy refresh discards old-generation records, shows the error and then replaces it with fresh results. Refresh becomes usable again.
- A controlled pending read shows “Reading this node…” and keeps refresh disabled until completion; it then renders all six. The page batches results: this does not prove progressive partial display or a never-resolving-request timeout.

Important display limit: fields are stored in **collapsed Native record details**. Four methods have friendly titles; assets/capabilities use the RPC name. There are no SwapNet summary metrics in the shared summary renderer. DOM text assertions do not prove default visual prominence, CSS, focus or screen-reader behaviour. We did not classify the expandable-record design itself as a defect.

## Reuse and finish line

This closes the admitted status display/error hypothesis at the source/DOM level. No repair or public success-only update is justified by this result alone. The earlier recovery-form repair821 is incorporated26164d1d; its tests need not be repeated. Forms/request-shape and generic native-approval contracts retain their recorded source/reused evidence limits. A **current native Atlas application connected to a node remains unqualified** by this check; neither whole Atlas/SwapNet acceptance nor release readiness is claimed. Start that additional work only for a specific valuable native-boundary question with feasible current artifacts, not just to fill another matrix cell.

## Evidence

- source-manifest.json:43 current source/test files, verified Git blob and SHA256 identities.
- coverage-comparison.json: per-method old/new scope and reviewed test inventory.
- reuse-comparison.json: byte-identical prior admission boundaries.
- qualification-receipt.json and diagnostic.log: exact command, runtime, elapsed time,11pass/0fail/0skip.
- source/gui/atlas/tests/swapnet-status-diagnostic.test.mjs: test-only diagnostic; not registered or published upstream.

Executed once: `node --test --test-timeout=10000 tests/swapnet-status-diagnostic.test.mjs` from the isolated source/gui/atlas directory, under a30second outer bound. Node reports66.6ms; outer process0.147s. The fifteen-minute execution budget was not approached. Over2GiB disk remained; no services/processes were left running. Reused JPP/Numair Atlas fixtures and prior contracts rather than rerunning209valid tests. New test files do not imply measured coverage percentage gains.
