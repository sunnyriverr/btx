# Operator CLI profile/mirror conversion — qualification evidence

**Fix06de33de: positional and named JSON request objects reach the helper as objects; the same maintained regression and real CLI workflow fail before and pass after.**

Code `06de33dea361e2d2ea612d9ffa13f2134b4d9845`, tree `e9846e9d1e930dbfc67436db6cbb0624077f4731`, base `666673a3153225ba264c7870e0e82e354df86765`. Two object-only conversion entries in src/rpc/client.cpp and one maintained test in src/test/rpc_tests.cpp;37addedlines total. This reuses the existing hostmodel object-only mode. Original source headers and upstream history are preserved; the correction/regression are by Sunny River. The separate Python mirror-wrapper fix is PR427.

## Measured before/after

[Native run42199048312](https://github.com/sunnyriverr/btx/actions/runs/42199048312), fixture `c64ee32f1868fc97e83292f962e0aed9ad44d86f`. Ubuntu24.04 x86_64, GCC13, OpenSSL3.5.9, disposable empty wallet-disabled regtest.

| Same test | Baseline | Corrected |
| --- | --- | --- |
| Maintained converter regression | fail, exit201 | pass, exit0;118assertions |
| Real CLI/node/helper workflow | fail, exit1;12of14requirements unmet | pass, exit0;14of14requirements |
| Bare custom positional/named | pass | pass |
| Direct valid/invalid controls and clean shutdown | pass | pass |

The exact regression object and functional script are shared between variants. Each workflow makes18real CLI calls. Patched profile requests save4MiB/6MiB and apply the effective quota. Mirror requests save both requested selectors while retaining an unrelated sentinel. Same-key/body retries succeed without changing saved bytes or deliberately old modification times; conflicting reuse reports IDEMPOTENCY_CONFLICT. Missing-key and nonzero-spend requests remain refused for the intended reasons and preserve both saved files. Read-only calls preserve files; automatic spending stays0; blockcount stays0. Baseline object requests refuse rather than overwriting settings.

The harness records unmet CLI requirements, then uses independent typed-object controls to leave equivalent state for later checks. Those direct calls are not counted as CLI success. Baseline's two missing-key requirements already pass; its other12fail. Both variants execute all direct valid/invalid controls.

## Reproduction entry points and provenance

Maintained case: `rpc_tests/rpc_convert_values_model_operator_requests` in the product commit. A normally built test_btx can select it with `--run_test=rpc_tests/rpc_convert_values_model_operator_requests`; that full-target recipe was not executed in this campaign.

The executed CI entry point is workflow.yml at `.github/workflows/operator-cli-repair.yml` in the fixture. It runs run.py phases preflight/dependencies/build/test/finalize with case.py, expected-inputs.json, code-identity.json (source-manifest.json here), regression.inc and candidate/src/... at `contrib/devtools/operator-cli-repair/`. Preserve that fixture layout to reconstruct the run. `records/result.json` records exact commands and durations; `records/baseline/observations.json` and `records/candidate/observations.json` contain returned/saved-state observations. The fixture and scripts above preserve the actually executed entry point; a fresh clean-build reconstruction is not claimed tested.

The native recipe restores immutable branch-scoped cache10096149671, verifies CMake flags/retained binaries/OpenSSL, rebuilds only unchanged helper target (4seconds), then compiles the maintained Boost body once. It compiles the baseline/candidate converter with the actual retained compile command, replaces only client.cpp.o in copied CLI archives and relinks two isolated CLIs with the retained link command. The same real node/helper serves both variants. Another account may not have access to that branch-scoped cache; the maintained test does not depend on it.

All14309accepted source blobs and modes match immutable Git inputs before/build/test/final. The original archives and node/CLI/helper binaries are unchanged; no cache save. Source audit identity and binary/harness hashes are in native-verification.json and records/collection.json.

Artifact13494220002 SHA256 `af4b3bacbfd23cdca5b803454392d6bacb458d9052a1df86b95aac44e082a84c` was digest-verified and all19,653,324expanded bytes inspected. Readable small records are retained here; the four full source-audit catalogs remain in the expiring runner artifact, with their complete hashes and local immutable-tree verification summarized in collection.json. The code/test, runnable fixture and result observations here remain after artifact expiry.

## Scope and cleanup

Node built with wallet/ModelnetON, wallet disabled and node-owned Modelnet runtimeOFF; real external helper on a Unix socket, network discovery/peers off. No wallets, model downloads, mining or funds. This proves converter behavior, real proxied CLI requests, saved/current runtime settings and preserved helper guards. It does not qualify the full test_btx/full functional suite, default-owned helper, restart/reload, native Windows/macOS, live-network or release behavior. No server/helper permission, idempotency or automatic-spending rule changes.

Both helpers exit0, nodes stop via RPC, no fallback signals or survivors, owned runtime removed. Source/binary preservation and artifact digest were independently checked by the collector against immutable inputs. Internal read-only review corrected an insertion conflict with pending423/425before execution; this new case precedes the bridge case. Internal review is not separate native platform verification.
