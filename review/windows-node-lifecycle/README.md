# Native Windows optional-helper lifecycle

**Tested PASS `473a2a0bf8e5`: startup, real RPC, same-datadir genesis restart and natural shutdown with an explicitly unavailable helper.**

- Source: swarm `666673a3` plus **#411 (`362c36b2`) and #415 (`a75dc8f6`)**, both still open/unmerged at submission. Exact tested tree `d860c05655a867235ca38e6e78d5b2431cc24a8f`. This branch descends from the actual executed source commit, so that source is retained in Git. Use [that source](https://github.com/sunnyriverr/btx/tree/473a2a0bf8e528a977d07137712d6a1d6dfc8cf6) for code review/builds; evidence-only commits were not compiled or run.
- Profile: Server2025 x64, clang-cl20.1.8, MSVC14.51.36231 libraries, SDK10.0.26100.0, static OpenSSL3.5.4; Modelnet/tests/wallet/ZMQ compiled ON. Runtime wallet disabled and networking isolated.
- Executed [run 42005749177](https://github.com/sunnyriverr/btx/actions/runs/42005749177), [controls 9a10584a](https://github.com/sunnyriverr/btx/tree/9a10584abf0ae93eab67bc6793b22c43ee4ff0ae/contrib/devtools/windows-root-configure). One cached 6-step node relink in 12.28s; only btxd.exe and normal Ninja logging changed. No object bytes changed or full-unit build attempted.

## Results

| Case | Real observation | Natural outcome |
| --- | --- | --- |
| Optional/default helper policy | No modelnet/required switches; explicit nonexistent modelhelper path, no substitute. getblockchaininfo/getnetworkinfo/getblockcount and five height/hash health polls. | RPCstop, exit 0; cookie removed, port closed, no children. |
| Same-datadir restart | New process with the same arguments/datadir; actual RPC, same genesis height/hash and fresh missing-helper diagnostics. | RPCstop, exit 0 and all cleanup checks. |
| Explicit modelnet0 | Healthy RPC and disabled-path diagnostics. | RPCstop, exit 0. |
| Explicit modelnetrequired1 | Same absent-helper fault returns the expected required-helper failure. | Natural exit 1, cookie removed/port closed/no children. |

[summary.json](summary.json) contains actual arguments, RPC responses, health samples, process snapshots and command hashes. The default-policy starts did not pass modelnet0; required1 is the positive path-control for helper absence. Restart logs were split at a prelaunch byte offset and verified as fresh records. No forced kills were needed. Healthy logs also record `GUARD_EXECUTABLE_ABSENT`.

## Review evidence

Start with [verification](verification.json), [original-record map](manifest.json) and the per-boot logs under records. All42native artifact members are retained byte-for-byte, with identical files deduplicated and their original names/hashes mapped. In particular, full source catalogs, checkpoint and frozen generated Ninja graph are preserved; no temporary Actions artifact is required to read the saved evidence. Large generated files are provenance records, not the reviewer entry point.

The verifier checked all 8 command logs,14,311 source entries, source/config/frozen graph/library/checkpoint identity, actual RPC results, exits and cleanup. [Internal result review](RESULT-REVIEW.md) is not independent human/platform reproduction. New executed binary SHA256: `35b0aa504dfde65843a12374c731799d92ac7f10b1ab002a5b699b87356be485`; original node before relink: `349c5d3c08b54a624aab32a2a4cdcf38f0412e1264a283daf7cdf52ee0ec94d9`. Source stamps and original execution/cache identities have not been relabelled to this evidence branch.

Exact source profile/checkpoint cache10047590725 was restored. New [cache 10050456328](cache-receipt.json) retains 3,830 objects, node 35b0aa50 and normal dependencies; original cache remains. Cache availability is separate from permanent evidence retention.

## Scope and remaining Windows gate

The missing-helper condition is a deliberate nonexistent -modelhelper override supported by init.cpp/HelperSupervisor::Start. This does not qualify automatic packaged discovery, a running-helper crash/recovery, helper transport/admission or a guard/protected workload. Fresh isolated regtest at height 0 only: no populated-chain restart, sync/catch-up, wallet/spend, mining/GPU, Windows11/fullcl.exe or release qualification.

**#356 remains open:** a complete maintained Windows test_btx build/run is still outstanding. PR415 fixes only the demonstrated fixture subsets; ten other grouped fixtures plus the earlier retrieval fixture remain. This is explicit #411+#415 candidate integration, not an accepted-stock result. No product code was changed for this test.

## Executed controls and reconstruction

The original CI workflow is copied in controls/workflow.yml, along with exact scripts/inputs/source bundle. The actual stages were lifecycle.py prepare/build/run/retain from the original contrib/devtools/windows-root-configure location at9a10584a. They rely on the recorded Windows tool environment and exact cached graph. Copies here are evidence of the executed entry point, not a newly executed standalone or fresh-build recipe. A missing cache is a prerequisite to resolve, not permission to substitute an unrelated mutable build. Never invoke default Ninja/CMake on that frozen graph without the recorded plan/source checks.

Credits: Windows prerequisite audit by repch1c and Jpp-matata (#356); original code authors remain on #411/#415. This result records our own native run.
