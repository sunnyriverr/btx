# Reproduce #275 item 6 scheduling starvation

Original finding: JPP's [item6](https://github.com/btxchain/btx/pull/275#issuecomment-6433856983). Target: `fd3a905fed3bc4943ad24372da032af4d29304a3` on the opt-in `btx-035/model-security-v2` branch. This change does not modify monetary consensus.

Prerequisites: a native Linux C/C++20 compiler, CMake, pthreads, SQLite development headers/library, and the repository's existing static probe. A static libc toolchain is needed for `security-probe` (the recorded execution used Alpine/musl/GCC14.2). Use disposable local test storage; fixtures contain synthetic identities and model bytes.

Create two detached worktrees from the exact target, then apply `tests.patch` to the baseline and `candidate.patch` to the candidate. Keep their build directories separate. For each worktree:

```sh
cmake -S test/util/model_security -B queue-build \
  -DCMAKE_BUILD_TYPE=Release \
  -DBTX_INTEGRATED_SOURCE=/nonexistent \
  -DCMAKE_EXE_LINKER_FLAGS=-Wl,-z,stack-size=8388608
cmake --build queue-build --target security-tests security-probe --parallel 1
results_dir=$(mktemp -d)
queue-build/security-tests queue-build/security-probe "$results_dir/results.json" scheduler-
```

`mktemp -d` supplies a private0700 report directory, required by the real `WritePrivate` API. Do not place the report directly in a0755 directory. The fourth argument selects the four scheduler cases; without it, the upstream test runner executes its full suite.

The independent-worktree recipe above is provided for review and has not itself been executed as written.

Both variants use the same test source. The recorded experiment links a baseline service translation unit before the same native component archive, while the above independent-worktree recipe builds each variant separately. No mock worker, altered admission rule or threaded runtime adapter is used.

The explicit ELF stack setting is material on musl: a measured default worker stack of133920bytes cannot accommodate the existing1MiB `artifacts::Stream` stack buffer; the configured stack measures8391456bytes. Keep the same setting on both variants. This is a configured Linux component result, not default Linux, macOS or release qualification.

Intended acceptance: the baseline should preserve valid-work/two-per-tick and pause/local-compute controls while missing-plan-prefix and preinsert-plan-binding cases fail because later valid challenge rows remain absent. The candidate should pass all four cases.

Observed unmodified baseline:1PASS/3FAIL. Both intended starvation signatures occurred and pause/local-compute passed. The seven-valid-job case passed its first-tick-two and all-seven-run-row checks, then unexpectedly found a completed evaluation with no signed report. Its exact worker error was not retained by the existing internal-task path. Four actual signed native PASS/dispatched receipt pairs were retained before/elsewhere in that sequence. Do not treat all baseline valid-worker controls as passing.

Observed candidate:4PASS/0FAIL with twelve actual signed native PASS/dispatched evaluation/receipt pairs. Reports preserve the envelopes in `scheduler_evidence`. One separately instrumented baseline diagnostic failed earlier at first-tick row count and recorded `SEC_CLOCK_ROLLBACK`. This demonstrates a baseline clock rejection, without proving the same cause for the original missing-report failure. It cannot erase that original failure. These results establish the scheduling regression/fix with an additional worker-control limitation; they do not qualify every native execution path.

The missing-plan case has70 lexically earlier uninstalled proposals, verifies exact32-ID page progress across service restart, then checks new lower IDs and a later installed approved plan after wrap. The preinsert case proves four earlier proposals fail the existing `SEC_TEST_PLAN_BINDING` check without creating run rows. The valid case observes exactly two evaluations in the first completed maintenance tick and eventual completion of seven valid challenges.

This fixes permanent prefix starvation for a finite backlog. It does not establish a25-second evidence deadline across the maximum16k retained proposals:32IDs per2-second tick can require roughly1024seconds for a full scan. Queue/result/running-task bounds remain unchanged; this is not a full-capacity continuous-protection qualification.
