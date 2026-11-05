# Remaining fixture native result review

5 November 2026. Bounded evidence/claim review of native run `41997202444` and candidate `473a2a0bf8e528a977d07137712d6a1d6dfc8cf6` (tree `d860c05655a867235ca38e6e78d5b2431cc24a8f`). Read the retained ZIP in place with zipfile, its `four.json`, original build/case logs, candidate inputs and the relevant current source bodies. No tests were repeated, no large files were extracted, and no source/Git/network/ledger mutation or delegation occurred. Only this reserved report was written. Parent independently owns full source/checkpoint/log-hash/cache and cleanup verification.

## Verdict

**PASS for the bounded native component result and its stated claims; no blocking issue found.** The actual build log shows compilation of all eleven selected maintained fixture translation units and successful linking of the explicit component. All thirteen requested cases actually entered and passed, with zero exit codes. The R2 case progressed through the Windows PATH refusal and successful scoped ENV setup into its complete byte/hash/backend-count oracle. Both Store2 positive cloud fallback and corrupt-data refusal controls passed. These results establish the measured fixture correction; they do not close full native `test_btx` or stock-node acceptance.

## Actual compile/link/runtime chain

`candidate/inputs.json` and archive `four.json` identify the same candidate `473a2a0b`; the runtime binary's recorded build info gives full candidate identity and `BUILD_GIT_DIRTY 0`. Archive source-catalog entries for the reviewed cloud units match the inputs:

| Source | Recorded working SHA-256 |
| --- | --- |
| src/test/modelnet_store2_tests.cpp | `5db43b2263011219ff40fb751be91e7624f95fb9333fc57b6ca5898c254c4b1f` |
| src/test/modelnet_r2_storage_tests.cpp | `140c6dff225ab9a9de578af4c450658b0a68cd5854a62828beb4c8917e30a74d` |

`focused-build.log` contains seventeen actual build steps and ends in the ordinary `vs_link_exe`/`lld-link` invocation for `bin/windows_fixture_boundaries.exe`. The eleven selected fixture source compilations are present: swarm node, clearing, liquidity, live, contract, gap, appointment, gate, accept, Store2 and R2 storage. The two additional production compilations are clientversion and the matmul production canary; these do not imply that the complete production closure was rebuilt. The retained generated entries identify the selected fixture commands and the actual Ninja log shows their dependency-tracking flags as well. No forced macro undef, renamed API or source substitution is used to pass these callers.

The component link block explicitly selects fifteen objects: eleven fixture objects, the maintained test main, lightwatch and two wallet test-fixture support objects. It retains project libraries including `bitcoin_modelnet.lib`. Its existence and successful link are evidence for this selected component, not for a full-unit executable. The executable SHA-256 recorded in `four.json` is `f7878539182f07ef0d1c9b4a479b740fc83e4f0de90c9902e22e958653cc612e`.

Both before/after library records identify unchanged canonical archive SHA-256 `4c924f0731642e0b8aedece02ba8a3229a59b254c0da20637aaea39db5fb529c`, with `?GetObject@S3PieceStore@modelnet...` in the filtered symbol evidence. Thus the new caller qualification links to the already-canonical library; this run does not claim a fresh declaration/definition repair or archive rebuild. The previous grouped diagnostic `41994623193` remains the real failing baseline for these two units.

Every `four-case-N.log` has an actual selected-case entry and detailed passed report matching the requested case, not just an inventory match or successful empty invocation. `four.json` records one started case and zero exit for each. In aggregate the thirteen distinct cases report 341 passed assertions. The log messages saying the other cases are skipped follow each explicit `--run_test` selector; they must not be described as passing complete suites.

## Cloud interface oracles

| Original log | Maintained case | Actual result |
| --- | --- | --- |
| four-case-10.log | modelnet_store2_tests/store2_02_tiered_miss_fills_local | 1 selected case passed; 10/10 assertions; exit0 |
| four-case-11.log | modelnet_store2_tests/store2_03_never_serve_unverified | 1 selected case passed; 13/13 assertions; exit0 |
| four-case-12.log | modelnet_r2_storage_tests/r2s_01_layout_identity_invariant_across_key_families | 1 selected case passed; 41/41 assertions; exit0 |

Store2 case02 establishes verified cloud-only residency and initial local absence, then calls the production `TieredPieceStore::GetPiece`. The production path calls `m_cloud->GetObject` through `CloudObjectStore`, checks the leaf, returns matching bytes and fills local storage; the test verifies BOTH residency. The actual fake override is therefore exercised across the production interface. Case03 retains the wrong-leaf refusal, tampered-local rejection/empty output, and tampered-cloud rejection with no local cached piece. Its passing result supports refusal of unverified bytes rather than merely successful nominal dispatch.

R2's generated command defines `WIN32`; the reviewed selected body therefore executes both `BOOST_CHECK(!file_store.Init(err))` and the exact mode0600 error check before the ENV-backed store. These are ordinary assertions, so accepting the PATH credential or failing for a different reason would make the case fail. The remaining body requires successful ENV-backed Init, source-file put/read and four direct canonical `S3PieceStore::GetObject` reads. It compares the whole and reassembled buffers with the original payload, compares SHA-384 for both, and verifies measured one-versus-four PUT/GET backend counts, alongside key/planning assertions. The original log does not print every passing expression, but its actual 41/41 report, the compiled Windows branch and the retained source chain support these outcomes. It is not evidence for a live R2 endpoint or for bypassing credential validation.

The scoped helper checks the ENV mutation and restoration operations. The candidate preserves its original environment value or absence after this case. Macro push/undef/pop preserves the post-include GetObject state and keeps the actual override/direct-call bodies canonical. The native result supplies the previously missing compile/link/runtime evidence for those bodies; source review alone had not supplied it.

## Honest limits and next decision

The run uses the retained native Windows clang-cl/static dependency profile, with the recorded runner-image transition `20261030.294.1 -> 20261103.298.1` and Ninja binary change. Do not call it an identical-host rerun. The component uses a private candidate and retained cache/prerequisite closure; it is not a clean accepted-stock-source build. Original full-unit configuration files remain the reference while a separate selected graph/executable is used for qualification.

The ten Swarm cases also actually enter and pass (277 assertions collectively). Their case names alone do not prove OS process isolation or any broader production/consensus property; the measured maintained assertions remain the evidence. This review's detailed correctness scrutiny is the cloud fixture/interface chain, with parent and the separate PID review owning the remaining source-contract checks.

Full `test_btx` compilation/link/execution, all48 cases present in this component, complete Store2/R2 suites, the remaining direct-header cohort, genuine live cloud/network services, POSIX execution, Windows11 interactive behavior and release qualification remain outside this result. In particular the other R2 PATH-credential cases were skipped; this result does not establish that their Windows setup succeeds. The retained prior full-unit failure is not converted into a pass by this component result.

After the parent's independent identity/cache/cleanup checks, this is sufficient bounded evidence to proceed to the already-authorized next integrated build step. No repetition of these passed cases is indicated absent a changed input or concrete unresolved failure. Publication remains held. Resource state: no execution resources used by this review and no other output written.
