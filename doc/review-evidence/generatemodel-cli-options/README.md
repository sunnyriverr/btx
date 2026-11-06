# Generatemodel CLI options — tested repair

**Fix `fae706ce2bb521984646baddf0f550ebeeb394d1` on `666673a3153225ba264c7870e0e82e354df86765`: the documented positional and named CLI object options work after one converter entry is added.** Code is on `codex/fix-generatemodel-cli-options`; this separate branch holds evidence only.

Before the fix, opts stay a string and the node returns RPC-3, “string is not of expected type object.” The same options as a raw object already worked through the real node/helper. The fix parses only opts as JSON, keeps model IDs as strings, and preserves server OBJ validation. The two-file commit adds one conversion entry and 37 lines of maintained tests.

## Executed results

[Native run 42170969509](https://github.com/sunnyriverr/btx/actions/runs/42170969509), execution fixture `16c3707b0b0754b2f3c1eabe7828d8253c3d7eb6`. One paired run, no repair pilots/repeats.

| Same acceptance | Baseline | Fixed |
| --- | --- | --- |
| Exact two maintained test bodies, standalone Boost runner |26 of 46 assertions fail; exit 201 |46 of 46 pass; exit 0 |
| Actual positional/named CLI → real node → real helper |both fail RPC-3; workflow exit 1 |both pass exact prompt/token count; exit 0 |
| Ten malformed/nonobject CLI controls per variant |all rejected, no adapter work |all rejected, no adapter work |
| Three typed raw-object controls per variant, including one after CLI probes |all pass |all pass |
| Raw-string rejection, endpoint/auth control, wallet-disabled genesis health and normal shutdown |pass |pass |

The positive adapter input is exactly `{"prompt":"hello-btx","max_new_tokens":8}`. The result is `echo:hello-btx`, backend `fake`, with zero automatic spend and no remote/server inference. The baseline deliberate final assertion runs **after** normal node/helper shutdown. Its framework log’s generic “Not stopping nodes” wording is not a leak: [shutdown-baseline.log](shutdown-baseline.log) records completed shutdown. Both helpers exit 0/remove their socket; the finalizer finds no process and sends no signals.

## Build/profile and limits

Ubuntu 24.04 x86_64, GCC 13.3, CMake 3.31.6, pinned static OpenSSL 3.5.9; wallet and Modelnet compiled ON. Actual maintained converter flags are C++20 / -O1; CMake removes NDEBUG. The standalone Boost wrapper is explicitly -O0. The exact new maintained bodies are compiled once, then linked against baseline/fixed converters; their shared test object is byte-identical. **The full test_btx target was not built or run.**

The node/helper are unchanged retained binaries. Both real CLIs were separately relinked from the same maintained link command/current libraries. Copies of the same CLI archive differ only in client.cpp.o; stdin/lightwatch member hashes match. Neither relinked CLI is called the original cached CLI. Original archives/binaries remain unchanged. Full input commands, member/binary hashes, configuration and the four 14,309-file baseline source audits are recorded in [native-result.json](native-result.json) and [artifact-verification.json](artifact-verification.json). Candidate source/body hashes independently match fae706ce.

Disposable wallet-disabled regtest at genesis; monetary network inactive, loopback bind, external Unix-only real helper, 16 MiB catalog, no peers/LAN/NAT/following/hosting. A 96-byte synthetic directory and explicitly fake local generate adapter follow the maintained modelnet_hosting_tests fixture contract. **This proves CLI conversion and node/helper/adapter transport, not actual LLM inference or GPU/device admission.** No clean full node build, full unit/functional suite, Mac/Windows, mainnet, populated-chain restart, default monetary validation or release qualification is claimed.

## Entry points and reconstruction

The actual executed entry point is the [immutable fork workflow](https://github.com/sunnyriverr/btx/blob/16c3707b0b0754b2f3c1eabe7828d8253c3d7eb6/.github/workflows/generate-cli-repair.yml). Its run.py phases are preflight, dependencies, build, test, finalize. The test phase compiles the exact [regression.inc](regression.inc), creates separate baseline/fixed CLI archive copies, relinks both and executes the identical [case.py](case.py). It accepts the baseline only when the expected conversion assertions fail while every control and normal cleanup succeeds. Raw results: [unit baseline](unit-baseline.log), [unit fixed](unit-candidate.log), [workflow baseline](workflow-baseline.log), [workflow fixed](workflow-candidate.log), [observations baseline](observations-baseline.json), [observations fixed](observations-candidate.json).

This executed recipe intentionally uses a verified, branch-scoped retained build at an exact path/cache key. Its guards stop on missing/different inputs; it is not an unmodified clean-build recipe for another machine. Reviewer reconstruction: build the maintained unit target for the selected checkout, then run `build/bin/test_btx --run_test=rpc_tests/rpc_convert_values_generatemodel_*`. That full-target invocation was **not executed here**. The new bodies live in src/test/rpc_tests.cpp; do not treat standalone-body qualification as full RPCTestingSetup qualification.

The earlier reproduction phase had three fixture/setup stops (requested-vs-actual CXX flags, conflicting listen/bind flags, Decimal logging). Those were resolved before this paired run and are not product fail-before/pass-after evidence. The repair campaign itself completed without such corrections.

Existing Bitcoin/BTX license headers and the existing hosting fixture contract are retained/acknowledged; no invented co-authorship or third-party platform execution. Logs are plain text with ANSI removed; selected shutdown lines and exact original/published hashes are documented in [source-map.json](source-map.json). No credentials, wallets, chain data or compiled binaries are packaged.

[verification.json](verification.json) and [manifest.json](manifest.json) describe the historical qualification, not a live merge/release status. Artifact 13481605429 SHA256 `eae6a2e374b6f0d2010747de3db171577e632e666e80d7e46dc8ba022b307442`, expires2026-11-13T05:53:36Z; verified and inspected in memory. Essential logs/commands are durable here.
