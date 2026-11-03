# Channel freeze and recovery

BTX test 1 delegated executor `channel_recovery_execution`. Immutable source `fd3a905fed3bc4943ad24372da032af4d29304a3`. Model setting inherited / unverified. Original report: Jpp-matata, PR275 finding5. Coordinator owns shared records, overlap decisions and publication.

Final baseline:4/6PASS, two intended failures. Repeated Tick on an expired retained active capsule revokes newly prepared unrelated permits (`Broker::Execute` returns `SEC_PERMIT_REPLAY`) and destroys a valid signed successor staged for canary. Initial freeze/global revocation remains correct.

The unchanged reviewed lifecycle-only candidate passed6/6 cases with the same final harness. The two recovery paths now complete: an unrelated permit performs the expected read after repeated Tick/reopen, and a signed successor survives canary, activates and supports the expected channel-bound read. First freeze/global revocation and all retained controls pass.

A preserved5/6 candidate pilot reached an incorrect negative-control expectation hidden by the earlier baseline target failure: Stage admits a capsule before checking sequence, so an already-expired capsule correctly yields SEC_EXPIRED_OR_FUTURE. With coordinator approval, the test retained that refusal using the correct error and kept separate valid-capsule gap/rollback controls. One final corrected matched baseline/candidate sequence then ran; product bytes did not change. This was a contract correction, not evidence that an expired capsule should reach the sequence guard.

## Test boundary

`harness.cpp` derives its fixture from repository `test/util/model_security/security_tests.cpp`. It uses signed synthetic policies, compositions, evidence capsules, owner mandates, channel updates and canary receipts; actual resident-file verification; public Lifecycle/Database/Broker methods; and genuine descriptor-scoped reads of a synthetic private workspace with exact digest checks. No SQL channel/permit bootstrap is used.

Canary receipts are synthetic signed admission fixtures spanning the policy interval, not actual sandbox execution. No Service thread, native worker, model, inference, public network, VM or production process runs. Main-thread component execution does not qualify the full daemon or default worker stack.

Operation timestamps are explicit historical virtual times, normally wall time minus5s and minus40s for a signed30s peer-lease case. Body timestamps, imports and transaction API samples stay consistent and monotonic. Product NowMs, CheckClock and authority/time guards remain unchanged. Broker effect/release callbacks still sample the actual wall clock. Database reopen means a second durable connection, not a Service boot/process restart.

The same final compiled harness object is used across variants. Cases cover first freeze/revoke; unaffected actual permit use after repeated Tick/reopen; valid successor preservation, activation and channel-bound actual read; ordinary-canary new active failure; narrowed runtime authority and revoked mandate/candidate/canary; wrong generation, insufficient duration/samples; qualified previous rollback and sequence controls; and signed peer eligibility recovery retaining existing eligible-old-active-during-canary behavior plus fresh subsequent same-generation failure.

The renewed-eligibility case is a compatibility control. A discarded permanent Broker quarantine would tighten existing dispatch behavior and was rejected in scope review; that earlier baseline expectation is not a third established bug. Selected code only acknowledges a current failing active generation, always rechecks eligibility/owner/previous, rearms after recovery, and leaves Broker unchanged.

## Build identities

Native macOS arm64, Apple C++, C++20, warnings as errors, real Homebrew SQLite. The matched before/after profile compiled the harness and relinked11 preserved fd3a security component objects with identified pr362 PQC/crypto/UniValue archives. Candidate substitutes only freshly compiled lifecycle.cpp. No Service code is linked into the test entry point.

A separate candidate-only repository-native integration also passed: a fresh Release build of the official component library and fresh crypto/JSON archives, followed by CTest `security-channel-recovery` (1/1PASS,2.24s; underlying6/6PASS). Only that target/test ran. All32 actual compile units were fresh;65 actual repository source/header inputs match fd3a or the exact accepted lifecycle/harness, with one identified Homebrew SQLite header. The full component library compiles Service.cpp, but the final executable has zero linked Service symbols and the test constructs no Service or worker. Native compile commands, library/binary hashes and CTest log are retained in `native-integration.json` and `native-build/`.

`source-closure.json` compares239 actual compiled repository inputs from retained dependency files against fd3a: all match. One generated header and original compile/link configurations are captured. Archive hashes match the pr362 receipt. This is a partial relink with identified historical dependencies, not a clean/full-node build or compiler attestation.

`baseline-build-run.json`, `candidate-build-run.json`, logs, result JSON and individually canonical signed-record JSONL retain exact input/output identities. Generated private keys and local configs are removed with each private fixture. Test source derives synthetic signer roles from the upstream fixture; two synthetic hosts on one machine do not demonstrate physical independence.

## Pilots and limitations

Preserved pilots show corrected fixture errors: Text rejected empty status fields; an identical replacement capsule body reused a revoked ID; and an aggregate record writer exceeded the per-record canonical size cap, corrected by independently canonical JSONL records. No guard was relaxed. The rejected conservative-policy pilot and unexpected candidate control result remain retained. Only the final matched harness establishes before/after claims. Final harness SHA256: `80be83e62a892fd3c69ccabd16ee27f157bd6bfae6f422afcd8c9d6e4fe40370`; tested lifecycle.cpp SHA256: `b3b085cc5a501b7a5218eedb90daf980d27717ef58481d2ea6653e99fd306d3d`.

No Linux/Windows/full-daemon, native sandbox, live-chain, release or independent human replication claim is made. A fresh Mac component build is distinguished from the original matched partial-relink experiment. Existing rollback's missing MeshRequireLive check is preserved, not repaired. Default-stack/325 stopped work remains untouched. No Git/GitHub/shared source/index/cache mutation or VM use occurred.

## Entry point and native integration

Local recorded entry point: `python3 work/btx-review-tools/channel-freeze-recovery/execution/build-run.py baseline` (exit1,4PASS/2FAIL). Candidate entry point is the same script with `candidate`; final result is exit0,6PASS. This requires retained identified local dependencies and is not a portable clean-build recipe.

Repository-native integration is staged and executed: `candidate/test/util/model_security/channel_recovery_tests.cpp` is byte-identical to the final harness; adjacent CMakeLists adds one executable, link to existing `btx_model_security`, and CTest entry. `product.patch` contains exactly lifecycle.cpp plus those two test integration files. No fixture/framework refactor was made.

The executed fresh integration entry point is `python3 work/btx-review-tools/channel-freeze-recovery/execution/native-integration.py` on an absent `native-build` directory. It selects the official standalone component project, exact staged overlay, read-only source dependencies, explicit Homebrew SQLite and serial target build, then only the new CTest. It monitors the40MiB task cap and1.25GiB reserve. The initial launch did not find bare cmake in PATH and did not configure/build/run anything; using existing absolute Homebrew tool paths fixed that routine setup error. The launch receipt is preserved.

All owned temporary fixture directories are gone and no owned test/build processes remain. Read-only dependencies remain preserved; task evidence, fresh build outputs and binaries total about21MiB, below the40MiB gate. Host free space after the native gate was about1.27GiB, above the1.25GiB floor. Executor build/runtime reservation is released; coordinator owns final review and branch/handoff decisions.
