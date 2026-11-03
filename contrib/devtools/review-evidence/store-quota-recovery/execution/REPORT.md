# Exact object-cap containment — BTX test 1

**PASS, synchronous native Mac component only.** On immutable baseline `fd3a905fed3bc4943ad24372da032af4d29304a3`, actual `objects` count 16,384 blocks new signed authority records but does not block a committing Broker pause or a fresh directly supplied owner-signed resume. Resume does not recover capacity. No product change is proposed.

## Observed result

One successful final invocation of the documented entry point passed both cases. The final result and retained signed public envelopes are in `results/result.json` and `results/result.json.records.jsonl`.

| Observation | Actual result |
|---|---|
| Below-cap valid descriptor-scoped Broker read | Dispatched, correct 21-byte content/digest; `sandbox_enforced=false` is expected for the read path |
| Below-cap signed revocation | Imported, stored and authoritative; grant release denied |
| Below-cap signed epoch-2 policy | Installed; active policy and epoch advanced; journal valid |
| Below-cap pause/direct signed resume | Committed; old prepared permit revoked; valid current grant usable after resume |
| Main fixture initial objects / added filler / final count | 34 / 16,350 / **16,384**, unmodified default quota |
| New valid signed revocation at cap | Exact `SEC_OBJECT_QUOTA`; no record or revoked-subject state installed |
| New valid signed epoch-2 policy at cap | Exact `SEC_OBJECT_QUOTA`; active policy remains epoch 1 |
| Atomicity of both rejected writes | All 19 SQLite tables, including objects, metadata/clock, permits, replay state and journal, retain identical row counts and ordered-content SHA-384 digests |
| Pause at cap | `paused=1`; prepared and fixture-injected executing permit rows become `revoked`; `CanRelease=false`; new Prepare gets `SEC_GRANT_REVOKED_OR_PAUSED`; count unchanged and journal valid |
| Close/reopen Database | Original connection destroyed before new connection opens same persisted file; pause and revoked phases preserved; release denied |
| Fresh owner-signed resume, supplied directly without import | Succeeds at count 16,384; control absent from objects before and after, present in `consumed_controls`; pause cleared |
| Resume replay | Exact `SEC_RESUME_REPLAY` |
| Old prepared/executing secrets after resume | Both exact `SEC_PERMIT_REPLAY`; new valid current authority can release and a fresh harmless read dispatches |
| Original storage capacity | Still 16,384 objects; another epoch-2 installation still exact `SEC_OBJECT_QUOTA`; policy remains epoch 1; journal valid |

The all-table snapshot hashes appear before/after quota failures in the JSON. Paused/final table digests and public record IDs also appear there. The original signed authority records remain available throughout the test. This does not claim that pause retroactively destroys every completed result or recalls external effects.

## Fixture and claim boundaries

- Real baseline `Database`, `InstallPolicy`, `ImportRecord`, cryptographic checks, `Broker::Prepare`, synchronous read `Execute`, `Pause`, `Resume` and `CanRelease` execute unchanged. No signature check or authority path is bypassed.
- The fixture uses generated ML-DSA identities, a real signed root-pinned policy, synthetic signed composition/evaluation/receipt/capsule attestations and a real harmless workspace file. The evaluation receipts assert fixture evidence; no model evaluation or multi-physical-host execution occurs.
- The 16,350 count fillers are **unsigned inert envelope fixtures inserted through `Database::Put`**, inside one setup transaction. They never enter `ImportRecord`, supply authority, or become referenced dependencies. This tests the real default object-count boundary, not end-to-end signed peer filling or a time-to-exhaustion estimate. First/last filler IDs and the complete objects-table digest identify this setup.
- Two permits genuinely pass Prepare. A fixture-only SQL transition changes the second durable phase to `executing`; Pause's invalidation of that row is tested. **No actual running task is cancelled**, and there are no threads, Service construction, native workers, VM, GPU or production/node processes.
- Database close/reopen is not guard/process restart, owner RPC/IPC latency, node startup, supervisor behavior or release qualification. A physically full database, page cap, journal growth, clock rollback, contention, expired authority and storage-capacity recovery remain separate claims.
- This is containment coverage beyond the existing JPP #275 finding 1 quota failures. Those known failures are boundary controls here, not claimed as a newly discovered defect. The earlier page-exhaustion/guard-start finding 4 is not rerun.

## Build and provenance

`build-run.json` records exact compiler commands, source revision, harness/binary SHA-256, 11 reused baseline security-v2 object hashes and source hashes, 25 repository dependency hashes checked against immutable Git objects, three archive hashes, SQLite header/library hashes, OS/architecture and resource observations. `source-identity.json` identifies the isolated exact baseline source slice. The lifecycle object is the **baseline** object from `pr275-runnable-queue/runtime/build`, not PR386's candidate lifecycle object. No Service object is linked. `prior-object-provenance.json` confirms that all 11 object hashes also match the recorded earlier exact-baseline channel partial link.

This is an explicit **partial relink**, not a clean source build. Retained objects use their original `-O3 -DNDEBUG -std=gnu++20 -arch arm64` configuration; the harness uses the recorded `-O2 -DNDEBUG -std=c++20 -arch arm64` flags. Native platform: macOS 26.5.1, arm64; Apple clang 17.0.0; Homebrew SQLite library/header identified by hashes. Crypto and UniValue archives match the previously identified channel baseline inputs. Nothing modifies those dependency objects, archives, dirty checkout, Git index or refs.

## Preserved output-path pilot

The first invocation completed both substantive cases (printed PASS), then aborted with `SEC_PRIVATE_DIRECTORY` while writing the result into the preexisting non-private execution directory. That is a harness output-path failure and **not a successfully packaged test**. Its log and build manifest remain as `pilot-output-path-run.log` and `pilot-output-path-build-run.json`. The entry point was corrected only to create/use a private `results/` directory. The next complete entry-point invocation retained all observations and exited successfully. Harness SHA-256 `b164b071893ad63079e5346ac927c30f7a42272e1ff72a361000d2a7cd083870` and binary SHA-256 `d1df2525edd15cbe42b01f9376c107e9a655593db38e47167f803b5377f4def1` are identical across both invocations. No product or assertion change, extra matrix, or retry after a safety rejection occurred.

Final invocation peak owned files: 15.046 MiB; minimum measured free space: 1.734 GiB, above the 1.25 GiB reserve. The script checks headroom and task size every 100 ms during each subprocess and uses one compile job. No unrelated cleanup occurred. Owned databases, workspace files and generated secret keys were removed by fixture destructors; `tmp/` was removed; dependency hashes remain unchanged. See `cleanup.json`.

## Handoff

Complete as component evidence, with no fix or publication. Coordinator BTX test 1 owns shared records and any external handoff. A separate recovery design is still needed before changing retention/emergency authority semantics. No repeat of this unchanged sequence is needed to increase a run count; actual guard restart would require a separately scoped integration decision.
