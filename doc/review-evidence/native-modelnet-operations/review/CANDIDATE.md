# Candidate 3 independent source review

Reviewer `/root/windows_boundary_review`, 4 November 2026. Scope: the three reserved candidate files compared to their baseline files and DESIGN.md. No builds, network reads, product edits or publication. Only this report written.

**Result: no blocking source issue found. Native compilation and behavioral acceptance remain unproved.**

## Exact inputs

Each baseline file is byte-identical to the corresponding planning snapshot: helper is exactly windows-compatibility-plan/403-helper.cpp; generate/pq1_runtime are the plan source/src/modelnet copies.

Candidate SHA-256:

- helper: `199a8b62dd524bf08d900913e671b5824a7de94f1c1c6f39f2c978476cc9b8f1`
- generate: `f6ec11f3880bb5d3f8af37cc014e8420a2b8a85fb5153c7e9bbf96452328786e`
- pq1_runtime: `9d936fa9e6483705a2d617679ac48156146ba71c36cf7969aa8d04a147656837`

A read-only conditional-source projection removed only the direct _WIN32 ifdef/ifndef alternatives, preserving all other preprocessor directives. The POSIX projections of generate and pq1_runtime are byte-identical to baseline. Helper changes in that projection are limited to the local WorkerPid alias/comment and four type-name substitutions: RunCudaLoader output type, ResidentCuda field, PidAlive argument and loadmodel child local. WorkerPid aliases actual pid_t on POSIX. No POSIX function body changed.

## Native boundary

The CUDA, adapter and llama guards return false before pipe, file or process operations. Optional inference returns true for absent/empty BTX_MODEL_INFER_CMD and otherwise refuses before operations. PidAlive is false; StopResidentLocked only removes impossible native stale state. WorkerPid is translation-unit local and a signed integer sentinel representation on native Windows; no HANDLE/PID conflation or global fake pid_t.

UnixSocketSafeToAdopt and UnixConnectedPeerIsSelf explicitly refuse native execution. ListenUnix refuses before even replacing its path argument, creating directories, unlinking or listening. CallUnixRpc refuses before connecting. WritePrivatePem refuses before open/truncate and cannot invoke the writer callback. These cover the two additional permission gaps identified in DESIGN.md.

Generate preserves its regular-file validation and rejects executable admission natively, which makes all four configured backend flags unavailable through ProbeHostGenerateProfile. Direct CUDA env invocation is independently guarded. OpensslBin preserves override precedence, including an empty override, then returns the existing CLI-name fallback natively. Its POSIX probe definition and use remain together in the POSIX branch.

## PR403 preservation

Exactly four calls remain in the candidate at helper lines 427, 556, 643 and 877 (CUDA, infer, adapter, llama). Their complete POSIX surrounding bodies are unchanged: pipe closes/dup2 first, descriptor cleanup next, exec afterward. Adapter parent-death/process-group handling is unchanged. The conditional util/subprocess.h include and cleanup definition remain as in exact403. No native child path or cleanup call remains executable.

## Nonblocking caveats and acceptance limits

- CloseWorkerDescriptors remains defined on Windows but all its calls are now excluded. A compiler enabling unused-function warnings as errors may reject it; if actual flags do so, guard the entire definition consistently with its POSIX callers rather than adding a fake native call.
- Existing source uses WIN32 while new guards use _WIN32. Verify the maintained native command defines both (as expected from the established project profile). A macro-only synthetic compile defining just one does not represent that profile and may expose old unguarded OwnerOnlyDir/parent-watch branches.
- Native RunCudaLoader leaves hold_pid untouched on false. Its current sole output caller initializes the variable to zero and checks the false return before reading/inserting it, so there is no live-state defect. Zeroing an optional output would be defensive consistency, not a handoff blocker.
- WritePrivatePem now safely refuses native private creation, but EnsureMlDsaTlsFiles still creates its parent directory first and accepts pre-existing cert/key paths as before. RunModelDaemon also mutates catalog/policy state before ListenUnix. Claims must remain about guarded operations; this source does not prove daemon-wide absence of mutations or new ACL validation.
- All platform evidence remains to be produced. Existing native header shims, remaining TCP/socket/signal uses and generated link dependencies require the complete maintained translation-unit compile. PR403 listener recovery requires the plan's actual affected Linux acceptance if include/link closure or exercised POSIX behavior differs.

Proceed with the bounded acceptance contract in the parent plan. No extra run is warranted solely by this source review.
