# Model identity labels: tested CLI repair

Fix `10f3a3bdc126c54e8fcb282afe9b4e5aceb78f7f` on `release-0.34.16` base `0ac06fd23b4a62038963fb29f1c77ab26d7a1346`: one conversion-row deletion plus the maintained `rpc_convert_model_identity_labels_are_literal` regression. Source is in this branch's normal `src/` tree and the focused code branch.

- Before: ordinary labels fail JSON parsing; Boolean/numeric/object/array-looking text fails node string validation. Literal `null` becomes empty and literal quotation marks are stripped. After: all supplied label text is preserved in positional and named requests.
- Compatibility: labels now use ordinary literal-string CLI semantics. Stop adding the old extra JSON quotation layer when you want an unquoted label. Supplied quotation characters are now part of the label. Direct typed JSON-RPC and omitted-label behavior are unchanged.
- Linux paired proof: the exact maintained test body fails before (exit 201, 24 failed assertions) and passes after (exit 0, 76 passed). The same actual CLI harness fails 18 of 20 requirements before and passes 20 of 20 after;27 controls pass each side, including direct/named/no-label/default identity, actual public-store comparisons and zero height/peers/spend.
- Scope: Ubuntu 24.04 x86_64/GCC 13.3/OpenSSL 3.5.9, cache-assisted normal current-source CMake CLI builds. The unit is a standalone extraction of the unchanged maintained case, not full `test_btx`. Real source-built CLIs use the same unchanged official586 daemon/helper package. No native Windows/macOS, full suite/RPC-help, restart, publishing, mainnet or release qualification. The archive producer build was not independently reproduced.

## Read the result

[Raw before XML](records/unit-baseline.xml), [after XML](records/unit-candidate.xml), [before actual CLI observations](records/baseline/observations.json), [after observations](records/candidate/observations.json), [machine-readable qualification](qualification.json), and [source/binary/input manifest](evidence-manifest.json).

[Native run 42368730374](https://github.com/sunnyriverr/btx/actions/runs/42368730374), fixture `239e30b24820950204052036b0310fbd77896dd1`. The successful job means the before/after proof and controls completed; the unmodified baseline product still fails. [Execution state](records/state.json) records commands, compile/link identities, timings, four 14661-blob source audits and cleanup. Complete source-audit data remains in the original digest-verified run artifact; its SHA256 is `cd8a02b585d37e46ce1c7c29f7ea6c19f3df3b05ad026a38c2609478d4945e02`.

## Executed entry point and reproduction boundary

The recorded workflow invokes `python3 contrib/devtools/identity-label-repair/run.py` with phases `preflight`, `dependencies`, `prepare`, `baseline`, `test`, `finalize`. The exact executed [runner](scripts/run.py), [workflow](scripts/workflow.yml), [actual CLI case](scripts/case.py), [maintained regression body](scripts/regression.inc) and [cache inputs](scripts/expected-cache.json) are preserved here. These scripts are archived under `scripts/`, while the original execution used the named `contrib/devtools/identity-label-repair/` layout and restored branch-scoped cache 10096149671. This evidence folder is not advertised as a fresh-host turnkey runner.

The maintained case lives in `src/test/rpc_tests.cpp`. Its ordinary full-build invocation is `build/bin/test_btx --run_test=rpc_tests/rpc_convert_model_identity_labels_are_literal`; that full executable was not built or executed in this qualification. The executed unit wrapper contains the verbatim case, compiled once and linked with each actual CLI converter object plus the same UniValue archive. Only `libbitcoin_cli.a` changes during the candidate rebuild. Normal CLI build timings are 23 s before and 3 s after; no source/dependency rewrite or broad test repeat was used.

The public-store/id/label comparisons are executed-case assertions; retained returned values, counts and digests do not independently reconstruct the omitted store contents. Research secret material and cookie files are absent. Both disposable runtimes were removed, no owned process remained, and the original remote cache was not saved or overwritten.

The actual backend is official asset 720210208 / 158893635 bytes / SHA-256 `58657765b5ac41252c44913f56c61247b781149fd21ed79374aedade67805ba1`, published for `0ac06fd2`. The annotated tag still peels to `d27530af`; this does not relabel earlier tests of the older `abf8cfb0` archive. [Qualification](qualification.json) lists full CLI and backend executable hashes.
