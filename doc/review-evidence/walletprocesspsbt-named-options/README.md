# Named wallet PSBT CLI conversion — native evidence

**Fix8d3f67e2: the same maintained converter regression and real wallet CLI workflow fail before and pass after.** Named adjust_timelocks, htlc_presign and p2mr_leaf requests now reach the existing wallet rules with the intended JSON types.

Code `8d3f67e20bc14f1e5edd49d9127047ca63a25d13`, tree `45b0b8a9bea2fff1163f327f9828198e0ed76bab`, base `666673a3153225ba264c7870e0e82e354df86765`. Three conversion-table entries plus one48-line maintained regression; two files,51addedlines. Wallet/server handlers are unchanged. Sunny River authored the correction and regression; original source headers and upstream history are retained.

## Actual results

[Native run42214444222](https://github.com/sunnyriverr/btx/actions/runs/42214444222), fixture `0729442e9432b339a884052a9a1a70979a8f940b`, Ubuntu24.04 x86_64/GCC13/OpenSSL3.5.9.

| Same test or control | Accepted baseline | Corrected CLI |
| --- | --- | --- |
| Maintained converter body | exit201/fail | exit0/pass,42assertions |
| Real wallet workflow | exit1/fail, four unmet requirements | exit0/pass, four requirements |
| Three valid named options | RPC-3: values arrive as strings | accepted, original PSBT returned |
| Whole-options and legacy positional forms | pass | pass |
| Wrong types and existing wallet guards | refused | refused |

Both variants use the same compiled regression object and wallet case, with an identical starting PSBT. Each workflow makes15CLI calls and three typed controls. All successful CLI replies (five baseline/eight candidate) and typed controls return the byte-identical original PSBT, incomplete with an empty input map/no signatures.

The disposable descriptor wallet has private keys disabled; the framework creates no default wallet and imports no keys. Every processing request explicitly sets sign=false/finalize=false. The PSBT has an unknown external input and an unfunded100-atom output to a validated public P2MR root. Wallet transactions/balance/UTXOs and mempool remain zero/empty, height0.

The negative presign=true request still has sign=false: the whole-options form returns `htlc_presign requires sign=true` before and after; the named form reaches that same guard after repair instead of its earlier type error. min_confirmations without presigning stays refused. String-valued Booleans and an array-valued leaf map remain type errors. These are refusal checks, not executed presigning or leaf selection.

## Entry points and exact inputs

The product adds `rpc_tests/rpc_convert_walletprocesspsbt_named_options`. A normal test_btx build can select that case with `--run_test=rpc_tests/rpc_convert_walletprocesspsbt_named_options`; the complete test_btx target was not built/run for this campaign.

The actual executed entry point is workflow.yml at `.github/workflows/psbt-named-repair.yml` in the fixture. It invokes run.py phases preflight/dependencies/build/test/finalize with case.py, expected-inputs.json, code-identity.json, regression.inc and candidate/src/... at `contrib/devtools/psbt-named-repair/`. Preserve that layout to reconstruct the executed recipe. records/result.json records exact commands/durations; records/baseline/observations.json and records/candidate/observations.json are the raw request/results. The phase named build verifies retained inputs; it does not build the node/helper.

The recipe reuses immutable branch-scoped cache10096149671 and verifies original node/CLI binaries, CMake configuration and private OpenSSL inputs. It compiles the maintained Boost body once, compiles baseline/candidate converter objects with the actual cached compile command, replaces only client.cpp.o in copied CLI archives and relinks isolated CLIs with the retained link command. No full root build, configure, helper build or cache save. Another account may not have access to the branch-scoped cache; the in-tree case is independent of it. A fresh clean-build reconstruction is not claimed executed.

native-verification.json identifies all source, original/isolated binaries and shared test hashes. All14309accepted tracked source blobs/modes match immutable inputs at four audit points; original archives and binaries stay unchanged. The collector independently compared complete audit catalogs to the immutable Git tree and verified all recorded requests keep signing/finalization disabled.

Artifact13499468837 SHA256 `6375ed3180be0defc1872f0890a666117d4ccf99ae9322cd04d386ae1fd773ab` was digest-verified and all19,575,666expanded bytes inspected. Readable small records are preserved here. Four full source-audit catalogs remain in the expiring runner artifact; exact hashes and their complete immutable-tree verification are retained in records/collection.json. The code, runnable fixture, observations and summaries remain after artifact expiry.

## Limits, setup history and cleanup

This is one native Linux pair using a real wallet-enabled node with Modelnet runtime disabled. The maintained Boost body ran standalone. No full unit/functional suite, native Windows/macOS, funded wallet, actual signing, timelock adjustment, HTLC presigning, nonempty leaf selection, restart or release qualification is claimed.

Earlier diagnosis had two setup-only pilots before any CLI comparison:42211454873omitted the test-framework wallet requirement;42211961780used an OP_RETURN output that BTX disallows. They are not product-failure evidence. The qualified repair pair reused the corrected wallet/P2MR setup and required no pilot rerun or changed acceptance assertion. Internal read-only review is distinct from native execution.

Each node stops through RPC; no fallback cleanup signal or owned survivor; temporary runtime removed. Production wallets/PQWallet and other sessions are untouched. No signature or broadcast occurs. All safety assertions and whole-options/legacy controls run before the final positive acceptance assertion, so the baseline failure does not skip them.
