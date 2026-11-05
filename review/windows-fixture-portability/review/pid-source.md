# Draft PID repair: bounded source review

5 November 2026. Session 1 child `/root/remaining_pid_review`. Verdict: **no correctness blocker found in the drafted PID repair; ready for the parent's exact-tree native qualification**. This is source review, not compiler/runtime acceptance or independent platform verification. Only this report was written; no source edits, tests/build execution, Git, CI, network, ledger action or delegation.

## Reviewed draft and authority

Read the actual `../source/src/test/util/process.h`, all nine fixture include/call sites, node's full scratch/descriptor implementation and test-util CMake conventions. Reused PID-DESIGN and the earlier inspection of the ten maintained filesystem cases. Parent reports grouped native41994623193 reproduced missing unistd in all nine pure-PID fixtures and reports an exact inverse text projection reproduces their prior bytes. That diagnostic and byte-comparison result are attributed to the parent; this review did not rerun them. The source is still uncommitted; the parent must pin the reviewed final tree before claiming native results.

The exact intended draft footprint is one new test-only header plus nine fixture files, replacing nine `<unistd.h>` includes and ten `::getpid()` calls. The nine files are `swarm_node`, `swarm_clearing`, `swarm_liquidity`, `swarm_live`, `swarm_contract`, `swarm_gap`, `swarm_appointment`, `swarm_gate` and `swarm_accept` tests. No broader socket/process/security semantics are repaired or qualified by this change.

## API, includes and namespace

- The header has the normal license text and unique `BITCOIN_TEST_UTIL_PROCESS_H` include guard. It selects `<process.h>` under `_WIN32`, otherwise `<unistd.h>`. This matches the existing native CRT/POSIX precedent in `modelnet/obs01/obs01.cpp` and avoids Windows SDK imports and a global getpid macro alias.
- `test::ProcessId()` directly calls `::_getpid()` on Windows and `::getpid()` elsewhere. Both calls use the actual process API, with no cached value, substitute identity, error-status emulation or environment-dependent fallback. `inline auto` preserves the API return type and is valid in the maintained C++20 profile; existing `std::to_string` receives the real numeric value.
- `namespace test` is defined at header scope before the fixture suite namespaces. All ten replacements use `test::ProcessId()`; no inspected fixture scope declares a conflicting namespace/object named test. The call in swarm_gap's anonymous namespace before its suite also resolves to the same helper. No new non-inline symbol or link library is needed.
- The nine replacement includes are explicit. The unchanged test target include roots already expose `test/util` headers. `src/test/util/CMakeLists.txt` lists implementation `.cpp` files, so this header-only addition does not require an artificial source-list/build-graph change.
- Native compiler `_WIN32` selection and the existing node `WIN32` descriptor guards are consistent for the retained Windows profile, which supplies WIN32 and is a native Windows compiler target. POSIX retains the actual unistd API and existing descriptor code.

## Preserved oracles and cleanup

The inspected node file retains **four** `#ifndef WIN32` regions: `OpenDescriptors()` definition, descriptor-count member, constructor snapshot, and Remove comparison. My earlier PID-DESIGN prose mistakenly counted three; the correct count is four. All four regions and `BOOST_CHECK_EQUAL(OpenDescriptors(), descriptors)` remain present. `ScratchDir::Remove()` still calls real `fs::remove_all` after the comparison on POSIX and directly on Windows.

Path prefixes, temporary-directory selection, create/remove calls, stream modes, lifetimes, product functions and assertion expressions remain the same in the inspected draft. The parent's exact inverse-projection check supplies the stronger byte-level no-other-body-change evidence. This patch does not relax node's descriptor observation, add synthetic Windows descriptor accounting, convert the probe file into an executable or change JSON/timestamp assertions.

The existing cleanup limitations remain evidence limits, not new defects introduced here: fatal requirements can bypass explicit Remove calls; PID paths are deterministic within one process; remove/remove_all outcomes are generally not followed by an asserted final path absence. Liquidity and appointment readers are constructed after scratch owners, so ordinary reverse destruction closes the readers before owner-destructor cleanup. A successful Windows removal is useful actual filesystem behavior, but not a universal proof that no share-delete handles exist.

## Meaningful native runtime set

The proposed ten registered cases remain useful and cover all nine changed translation units and both PID sites in swarm_gate. They exercise the actual filesystem paths, unlike arithmetic-only neighbors:

| Registered suite/case | Main qualification value |
| --- | --- |
| `swarm_node_tests/records_a_second_process_can_read` | Multiple real record writes/reads and explicit ScratchDir removal; POSIX additionally executes descriptor comparison. The case does not itself spawn another process. |
| `swarm_clearing_tests/persist_then_load_restores_balances` | Persisted clearing JSON/reload, replay/missing-read controls, destructor cleanup. |
| `swarm_liquidity_tests/shared_capacity_reservations_persist` | JSON persistence/parse/reload with frozen reservation state and destructor cleanup. |
| `swarm_live_tests/publish_keeps_four_bit_in_the_family_only` | Empty-directory control, scratch recreation, actual publish/read and exact timestamp no-rewrite oracle. |
| `swarm_contract_tests/command_log_persists_vote_and_keeps_the_prefix` | Real vote/log/commit persistence and reload with explicit removal. |
| `swarm_mandate_tests/a_mandate_cannot_assign_more_than_collateral` | Real mandate persistence/reload and conservation checks in swarm_gap. |
| `swarm_appointment_tests/hashlock_remedy_writes_and_reads_back` | Actual appointment write/JSON/readback followed by destructor cleanup. |
| `swarm_cohortbook_tests/expiry_revoke_stale_epoch_replay_and_rejoin` | First swarm_gate PID site: persistence/reload and admission-state recovery. |
| `swarm_verify_tests/a_checkpoint_stays_closed_until_every_child_matches` | Second swarm_gate PID site: persistence/reload retains incomplete activation gate. |
| `swarm_accept_tests/an_unmeasured_engine_is_not_advertised` | Real probe-file creation, close-before-status, missing/installed/unqualified controls and removal. |

Native compilation should use all nine original generated object commands; runtime evidence must identify the actual linked component or maintained binary and exact final source. Selected case success cannot substitute for compiling all nine objects. Conversely, compilation alone cannot qualify real temp-file/read/cleanup behavior. The source review establishes that the helper uses the real PID; these filesystem cases are not standalone PID-identity assertions.

## Next gate and limits

Parent pins the final tree, verifies the narrow footprint, then qualifies the same generated objects and the named maintained cases with truthful cleanup evidence. Preserve relevant POSIX execution of node's descriptor path. Other socket/process/security fixtures remain unchanged; no emulated safety/success or whole-file exclusion is proposed. Any remaining full-unit barrier is reported on its own evidence.

No full maintained unit link/run, stock-source/release acceptance, socket transport support/refusal conclusion, publication or production action follows from this review. Parent retains the booked task/path and all holds. This child acquired/released no resources.
