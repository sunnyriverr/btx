# Final verdict — discriminating cap proof accepted

Local test-only commit `3655ce1a9e6f9f41f9b4a37906701f045a2c46fd` is ready for the coordinator’s next scoped handoff. It has exact parent `6478f640e6a8a3cf464ddb33d05a54ef61e2cf3e` and changes only `test/util/model_security/security_tests.cpp`, SHA256 `5333ef047469e7c628ff1c76b4b4aecc249b5575e01510b21a81e4f42a1f9bc1`. No production code, API or diagnostic hook changed in this commit. The #384 timing prerequisite is an identical runtime test input on both variants, **not part of the test commit**.

The first primary entrypoint ran once in31.48seconds. Cap2 passes: its completed-first-pass cursor equals the independently sorted second endpoint ID, observed6894microseconds after the pre-constructor steady timestamp. The single `==2`→`==99` mutation clears the tail cursor at12556microseconds and fails **only** the final budget assertion. Both samples are safely inside the1.5second observation window, before the minimum2second second-pass boundary.

Both variants complete all7 genuine native PASS/dispatched report/receipt endpoints before the final budget check, so the mutant failure is not worker throughput, clock failure, cancellation, deadline miss or failed recovery. The observed metadata plus7-eligible/unique/no-other-producer/queue8>7 premises establishes the controlled first-pass submission bound. It is not a literal private queue counter or a general saturation/backpressure/stress proof. The timing window is an explicit fixture premise tied to the exact2second Maintain interval; missed windows are fixture failures and must not be rerun until green or claimed as cap defects.

FINAL-ARTIFACT-AUDIT.json records independent source, identity and native endpoint checks. The actual cap2 Service equals381 plus the one #384 dispatch change; cap99 differs only by the cap literal. All available saved executable/harness-object hashes match recorded identities. Reviewer recomputed all14 receipt RecordIds, actual probe runtime SHA384, expected output digest/length/exit0 and report/receipt challenge binding. Signatures are present and verified by the production import path; reviewer did not independently execute crypto verification or repeat a test.

Scope is one native aarch64 Alpine/musl component environment, explicit8MiB ELF stacks, exact common #384 prerequisite and identified reused crypto/JSON archives. It is not an unmodified381 runtime test, fresh whole dependency build, default-stack/other-platform/full-daemon/release qualification, or a rerun of the starvation/clock matrix. Existing source bounds and negative cases remain separate. No extra restart matrix was added for this test-only oracle.

The reproducer README now describes exact dependency archive hashes, recorded platform, official dependency target acquisition and the prior public384 source-build route. The extra acquisition commands were not executed in this cap experiment; no portable turnkey fresh-build claim is made. This resolves the material handoff gap without more execution. No material final source/documentation issue remains, and no additional test is required for this scoped correction.

Cleanup readback confirms no owned processes/fixtures/guest directory, unchanged646cached source files and cached libraries, no new packages, and VMStopped. The local receipt records no push. Reviewer output reservation released; reviewer performed only read-only source/Git/artifact review and writes here. Coordinator owns shared records and any later authorized public handoff. No #325 or production work occurred.

The following source-contract review is retained as the exact-target rationale.

---

# #381 cap-test oracle review

**Design accepted: use the durable cursor after the first completed maintenance pass, with an explicit steady-clock observation window, rather than count running/evaluation rows.** This is a test-only correction; no production API or scheduler instrumentation is needed. No execution was performed by this reviewer. Exact target #381 `6478f640e6a8a3cf464ddb33d05a54ef61e2cf3e`; model inherited, exact setting unverified.

## Defect in the old assertion

`security_tests.cpp:497–503` observes two evaluation_runs rows shortly after the first pass. Service starts exactly two workers (`service.cpp:89`), and evaluation_runs is written by worker admission, after queue submission. This therefore samples throughput, not accepted jobs per pass. repch1c comment6590244829 shows changing the cap2 comparison to99 still passes the assertion. Independent Mac results used SQLite/heap prerequisites and unsupported-worker BLOCKED endpoints; they are not new native-worker or timing-fix qualification.

## State owner and source contract

Submission ownership is Service::Impl::Submit: under one mutex it checks queue<8 (`:133`), task-map<64, inserts an internal name (`:139`), records the task and pushes the queue (`:141`). The two workers consume from that queue and erase internal task/name state on completion. Durable evaluation_runs is later authority for attempted execution, not enqueue acceptance.

Maintain is the only automatic evaluation producer. It first schedules at most2 canary jobs, then challenges, then optional remote work. Public Handle can enqueue explicit evaluate/work/canary/execute/resident-import/stage tasks through the same Submit with internal=false. The cap fixture must exclude these other producers, channels and remote work. A fresh isolated Service has empty task/queue/internal-running containers.

The challenge query (`:276`) materializes a fixed ordered vector, at most32 IDs with no attempt row for this evaluator. Before inspecting each ID the cursor is persisted (`:281`). Local-plan absence and an existing internal-running name can skip submission. Each successful Submit increments submitted; exactly2 breaks (`:296`). Finishing a short full result vector clears the cursor for next-pass wrap (`:301`). At normal pass completion, maintenance_error is cleared and maintenance_at updated together in a transaction (`:327`). The loop then waits2seconds using a stop-only predicate (`:348`); ordinary worker/queue notifications do not start the next pass early.

## Smallest discriminating fixture and proof

Before Service creation, create exactly7 distinct, lexically sorted challenge IDs, all with an installed valid owner plan, current identity/policy and matching suite/sample/gate. No prior evaluation_runs, canary channels, remote work or explicit job submissions. Verify initial maintenance_at absent. Keep config unchanged during the sample. Use the existing lean fixture so its default6 unrelated challenge records are not imported.

There is then a bijection between every first-pass inspected row and a successful Submit: no missing-plan skip; a unique name cannot already be internal-running before its first submission; initial queue/map are empty; with only7 submissions queue capacity8 and task capacity64 cannot be exceeded even if workers consume none. Worker admission/finish timing cannot change the already materialized vector or make a new unique name already running. maintenance_error must be empty.

Therefore cap2 ends its first pass after2 accepted jobs, cursor=sortedIDs[1]. The sole cap99 mutation accepts all7 and reaches the short-vector tail, so cursor is cleared. Both facts are independent of the number of worker threads or completed run rows. This is a controlled submission-bound proof for the prepared fixture, not a general queue/backpressure/stress oracle or a literal public queue counter.

## Observe exactly one pass without a product hook

Start std::chrono::steady_clock immediately BEFORE the Service constructor, so a pass starting during construction is included. Wait for the first completed maintenance marker. Capture maintenance_at, maintenance_error and the evaluator-specific cursor in one SQL SELECT snapshot. Require the entire observation through completion of that read to finish within1.5seconds, strictly before Maintain’s minimum2second inter-pass wait. Require marker newly populated and error empty.

This deadline is an explicit fixture precondition. Missing it means the first-pass observation window was missed; do not classify that as a cap regression or retry until green. Timing at/after construction or only checking that the marker stayed unchanged around a read is insufficient: a second pass writes its cursor before replacing its old completion marker. The steady bound before2seconds excludes that race. If the production wait changes, this exact-target premise must be reviewed.

Keep the captured verdict immutable while recovery runs. Do not reread the cursor at the end, after later wraps. Finish all7 genuine native jobs on BOTH cap2 and cap99 variants, preserving all signed PASS/dispatched reports and no worker errors. Assert the saved budget verdict last, so mutant failure is specifically over-submission after successful work rather than an unrelated worker failure or deliberate early shutdown. No additional restart matrix is needed for a change only to this oracle; existing restart coverage stays separate.

## Permitted experiment / acceptance

Coordinator’s fresh overlap review found no duplicate/new owner and authorized the executor. Same native fixture and final harness object for cap2 and the single mutation `if(++submitted==2)`→99. Use identical exact #384 timing prerequisite and8MiB configured Linux stack on both sides, because the known independent clock failure must not contaminate this cap proof. Disclose this as #381 plus a common reviewed #384 prerequisite, not unmodified6478 or default-platform qualification.

PASS condition: cap2 captured first-completed-pass cursor exactlysecondID and all7 jobs finish legitimately; cap99 captured tail-clear cursor (not merely timeout), all7 jobs also finish legitimately, then the saved budget assertion fails. Neither outcome relies on evaluating only2 running rows. Retain the constructor-to-snapshot steady duration, atomic3-key values, sorted7 IDs, errors, exact service/harness/prerequisite identities and raw endpoints. No cap changes should ship; only the stronger test assertion/fixture change belongs in #381.

Pitfalls: >8 offered jobs can turn queue saturation into the failure; background default challenges introduce skips; duplicate IDs can defeat the bijection; timeout or stale marker alone is not a cap observation; changing pause/local policy while sampling can cancel workers and alter acceptance; adding a production inspection API or a broad scheduler framework is unnecessary. Record sibling remote-work findings only; no #325, production or public write is in this review scope.

Status: exact test diff and the two native artifacts are now accepted. The final verdict and limits above supersede the initial design checkpoint. Reviewer reservation is released; no reviewer build/VM/runtime/Git/publication operation occurred.
