# Full-store recovery: containment exists, restoration is not implemented

Owner: BTX test 1. Source: `fd3a905fed3bc4943ad24372da032af4d29304a3`, PR #275's unchanged `btx-035/model-security-v2` head, checked 3 November 2026. This is proposed Modelnet security-service code, not monetary consensus or a diagnosis of the live BTX chain.

## Decision

Do not implement arbitrary pruning, raise the quota, or move revocation earlier as a purported recovery fix. The existing owner pause is a source-supported containment path at the **object-count** cap, provided its transaction can commit. It does not free capacity. A complete recovery fix needs bounded retention and emergency-control persistence semantics first.

## Existing evidence and coverage delta

[JPP's #275 findings 1 and 4](https://github.com/btxchain/btx/pull/275#issuecomment-6433856983) already report native Mac component reproduction: continuous evidence fills the 16,384-object store, new policy/revocation fail, and a separate event-journal/page-cap experiment prevents guard restart. We did not rerun those or claim their reproduction as ours. His 542-round/3.8-hour estimate depends on the stated six-gate/two-evaluator/25-second configuration; it is not a universal lifetime.

Fresh authenticated API snapshot: 103 open PRs (`open.json`), unchanged #275 head (`pr275.json`), discussions in `275-comments.json` and `386-comments.json`. No submitted quota/retention recovery fix found in this snapshot and relevant #282/#291 repair scopes. Unpublished work and every line of every PR were not independently qualified.

This review adds the supported containment/recovery distinction and transaction/retention constraints. The matching synchronous Mac component test is now complete: two final cases pass at the real default cap. [Execution and limits](execution/REPORT.md), [recipe](execution/REPRODUCE.md), [raw result](execution/results/result.json). It does not qualify owner-RPC latency, Service/guard restart or physical database exhaustion.

## Two limits, different failure modes

| Boundary | Source result | Recovery implication |
|---|---|---|
| `objects` reaches 16,384 | `Database::Put` rejects a new ID with `SEC_OBJECT_QUOTA`; an existing ID can merge signatures. | New signed revocation and policy fail; pause/resume have no `Put` call. |
| SQLite logical page limit (131,072 pages), physical disk exhaustion or another database write failure | Metadata, permit and journal writes can fail too. | Do not promise pause or restart will succeed. Object capacity and total database capacity must be tested separately. |

`database.cpp:59` sets max_page_count; actual bytes depend on page size. It is not a separate bound on WAL size or all directory bytes. `database.cpp:155–190` implements Put; `:131–143` implements rollback-on-uncommitted transaction.

## Supported containment, with precise limits

- `modelsecurity` is a local owner RPC, not a public PQ1 operation (`src/rpc/modelnet.cpp:2427` and `ARCHITECTURE.md:9`). `Service::Handle` maps `pause` to `Broker::Pause` (`service.cpp:473–478`).
- `Broker::Pause` (`broker.cpp:522–528`) transactionally writes `paused=1`, revokes prepared/executing permits and journals the pause. It creates no object row. This is the documented incident-handling first step (`OPERATIONS.md`). It can still fail on strict clock rollback, contention or total storage failure; no successful pause may be inferred from an attempted request.
- `Broker::Authorize` checks paused state (`broker.cpp:295`); execution rechecks authority before effects and output release, and queued read-output release uses `CanRelease` (`service.cpp:350–363`). A committed pause therefore has source-backed effect/release protection rather than merely a cosmetic status flag.
- Service startup invalidates outstanding permits and records a new boot without clearing paused state (`service.cpp:77–86`). The existing `feature_model_security_v2.py:42–51` covers ordinary pause across restart, **not** pause at full quota. No new full-store restart was executed here.
- `Broker::Resume` (`broker.cpp:530–555`) directly checks an owner-signed, current-policy, fresh one-use control and persists its ID in `consumed_controls`, without importing it into objects. A fresh resume therefore is not intrinsically blocked by the object cap. **It is not capacity recovery and should not be used to declare the full-store incident resolved.**

## Why the obvious patch is insufficient

`InstallPolicy` stores the new signed policy before changing active policy/epoch (`trust.cpp:134–155`). `ImportRecord` validates authority, starts a transaction, calls Put, then applies a revocation (`trust.cpp:381–391`). Moving `Revoke` before Put inside that transaction still rolls it back when Put fails. Moving it outside the transaction instead creates an unreviewed split between authoritative state, signed evidence and the audit journal. Skipping signatures, epoch checks or persistent replay protections is not a recovery design.

There is no supported object-pruning, quota-reset or journal-checkpoint/rotation operation in this source. SQLite's WAL checkpoint is not application-level retention. `VACUUM` cannot remove live object rows. Restart does not reset the object count.

## Retention constraints before implementation

A safe design must explicitly retain or replace, with equivalent durable semantics:

1. Current pinned-root policy, epoch floor, revocations/tombstones, monotonic clock and consumed-control history needed to prevent authority rollback/replay.
2. Active/previous/candidate channels, grants, composition ancestry, referenced signed challenges/reports/receipts and required negative evidence. Age alone does not establish that a row is unreachable or irrelevant to admission. In particular, trust.cpp:438–447 intentionally treats a retained FAIL signed under current evaluator policy as negative evidence after its positive freshness window; deleting such a report can change an admission decision.
3. Permit/job/budget and evaluation/trial state required to avoid reusing consumed authority or resetting limits.
4. Journal continuity and an authenticated archival/checkpoint contract; deleting events and resetting the journal head is not an equivalent audit trail.
5. Bounded, durable emergency-control capacity even when ordinary evidence is full; a row reserve alone does not solve physical disk or global page exhaustion.

Deleting `security.sqlite3`, replacing the security directory or directly editing revocation tables is not an established safe recovery workflow. Such actions can discard the very state above. Nothing in this review authorizes an operator action.

## Focused experiment completed

The final documented entry point passed both cases on baseline fd3a: a below-cap valid authority/read control and the exact-default-cap containment sequence. At 16,384 objects, new correctly signed revocation and epoch-2 policy fail with `SEC_OBJECT_QUOTA`; all 19 table snapshots remain identical around these rejected writes. Pause commits, revokes prepared plus fixture-injected executing rows, blocks authorization and new permits, and survives closing the original database connection and opening the same file again. A fresh owner-signed resume supplied directly succeeds without an object insertion, refuses replay, and never revives old permit secrets. A fresh harmless read works after resume; policy installation still fails because the store remains full.

The count was constructed with 16,350 unsigned inert envelopes through Database::Put, alongside 34 signed fixture records. This is a real default-count boundary with real cryptographic control checks, not signed network filling, actual worker cancellation or a time-to-exhaustion measurement. The executing row is fixture-injected; no task was run in a worker. No product code was changed.

A separate actual owner-RPC/guard-restart boundary remains untested and is not automatically selected as another run. The main remaining design decision is durable emergency-control capacity and retention that preserves negative evidence, authority/replay state and audit continuity. Source review and this component result do not resolve that policy or justify arbitrary pruning.

## Execution and resource limits

Disk initially measured 1,223,796 KiB free, below the existing 1.25 GiB test reserve, so execution was held. A later check measured 1,906,140 KiB after external/system reclamation; we deleted nothing. Final invocation peak task usage 15.046 MiB and minimum measured host free 1.734 GiB stayed inside the 100 MiB growth/1.25 GiB reserve contract. Retained output is~2.16MiB; owned fixtures, databases and generated secret files are removed, and reused dependencies remain unchanged.

Native macOS 26.5.1/arm64, Apple clang 17, identified Homebrew SQLite; partial relink of exact baseline component objects and archives, not a clean source build. Harness SHA256 `b164b071893ad63079e5346ac927c30f7a42272e1ff72a361000d2a7cd083870`, binary `d1df2525edd15cbe42b01f9376c107e9a655593db38e47167f803b5377f4def1`. First invocation printed both PASS lines but failed output persistence with `SEC_PRIVATE_DIRECTORY`; retained pilot is not counted as a successful packaged run. Only the driver output directory was corrected; the final invocation used the same harness/binary and retained all observations successfully. See execution/REPORT.md for full provenance and limits.

No Service threads, worker, VM, GPU, product change, GitHub publication, production node/wallet/miner or stopped-task retry. Database close/reopen is not guard/process restart. No new retention fix is selected. Exact source hashes are in source-identities.json; the source review and final artifact audit are in review/. Next: use this result to settle the emergency-capacity/retention contract before implementing recovery; do not repeat the unchanged experiment or add a generic quota bump.

## Final review and closeout

[Independent artifact review](review/FINAL-ARTIFACT-AUDIT.md) accepts the stated component scope; all 45 manifest entries match, with 11 historical component objects and 25 repository dependencies verified. One recipe wording overclaim about automatic object-byte hash pinning was corrected; no product, harness, binary or assertion changed. This is internal source/artifact review, not independent human or other-platform reproduction. All task resources are released.
