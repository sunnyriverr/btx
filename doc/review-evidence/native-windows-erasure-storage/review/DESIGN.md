# Independent storage portability design review

Reviewed immutable accepted source `ab1b5cbe42d5b3ceb4faafff213292efed2bba18` plus already-delivered prerequisite `3c542cd6800755a891cd3ffafd839fd682e7ec40`. Read-only source/design review; no product edits, build, VM, GitHub call or ledger mutation. Reviewer output is this file only.

**Proceed with a bounded storage portability repair, but a literal include guard alone is insufficient qualification.** The diagnosed production compile failure is real. This file writes binary model data and needs an actual native byte-preservation test once it compiles.

## Smallest coherent scope

1. Replace unconditional `erasure_store.cpp:20` Unix include with a platform split: native Windows `<io.h>`, POSIX `<unistd.h>`. Keep required standard declarations explicit (e.g. `<cstdio>` for rename/unlink-family context as appropriate; unlink itself is io.h/unistd.h). The production Windows forced compatibility header remains a declared prerequisite for `ssize_t`, `fsync` and current O_NOFOLLOW semantics. Do not introduce a global empty unistd shim.
2. Open this output in binary mode on Windows. The existing `::open` at line308 supplies `O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW` but no binary flag. Native CRT default text mode can translate LF writes. Use a local flags variable and add `_O_BINARY` under `_WIN32`, retaining exact POSIX flags. This also gives MinGW the desired binary behavior; do not claim its runtime without execution.
3. Keep the existing operation order and error handling: remove stale temp, exclusive create, bounded shard writes, fsync, close, complete I/O admission, rename, remove temp on write/rename failure. No codec, manifest admissibility, hash, authority, or validation changes.

## Existing semantics that must remain explicit

- `RepairStripeFromFiles` removes its `.tmp` name before opening. It therefore does not promise refusal of every pre-existing temporary file; `O_EXCL` only controls the subsequent creation. A meaningful collision/refusal control can use a directory occupying the temp path, rather than claiming an ordinary stale file is preserved.
- On Windows the existing forced header maps `O_NOFOLLOW` to0. This patch must not add a claim of Windows symlink/reparse refusal. Do not expand this repair into a new filesystem security mechanism.
- Windows CRT `rename` refuses an existing destination whereas POSIX rename may replace it. Preserve this pre-existing difference and test it according to each platform's behavior. Do not silently introduce replace-existing Windows behavior.
- `btx_fsync` delegates to `_commit`. Successful return is evidence that the existing flush call succeeded; it is not a power-loss durability qualification or directory-sync guarantee.
- Current third argument0644 includes POSIX group/other mode bits. Microsoft CRT documentation normally names `_S_IREAD|_S_IWRITE`. Observe the actual native production call before deciding whether mode conversion is required; do not manufacture a change from source inference alone.
- Existing short-write detection and cleanup are useful controls. A new general retry loop is not justified by this compile diagnosis.

## Discriminating test plan

Run exactly the same complete production-TU compile on baseline-plus396 and candidate under cl and clang-cl. Baseline should retain the measured missingunistd diagnostic; candidate must get through all source compilation rather than merely include a header. A successful build of a wrapper that excludes the function is insufficient.

For actual runtime, call the real `RepairStripeFromFiles` with genuine small shard files and the real codec/reconstructability/hash/I/O dependencies. Include arbitrary bytes with LF, CRLF, NUL and0x1a and compare exact output length/content. A header-guard-only intermediate or targeted binary-flag revert can demonstrate that the byte assertion catches text-mode corruption; it need not become another product commit. Keep compile-fail baseline distinct from an intermediate runtime control.

Useful controls: reconstruct from a genuine valid shard subset; wrong shard size/missing shard rejected without output; malformed/duplicate positions rejected; temp path occupied by a directory refused and preserved; successful output leaves no temp; rename refusal cleans the temp and leaves the original destination unchanged on Windows. POSIX counterpart should retain its existing replacement behavior. Keep output/data in owned disposable directories and verify cleanup.

Do not stub `ErasureManifestReconstructable`, SHA-384 or codec behavior. Real `erasure_store.cpp`, `erasure_manifest.cpp`, `io_executor.cpp`, `types.cpp`, `sha384.cpp` and their actual dependency closure are an appropriate starting point. Function-level packaging/linker dead stripping can avoid unrelated JSON entry points, but record that scope explicitly; it is a component runtime, not complete Modelnet linking. Missing real dependencies are harness/setup failures, not another product bug.

## Qualification limits and delivery

The previous native diagnostic used explicit component flags and /MD, not root-generated static-CRT flags. Retain that distinction, exact source/header prerequisite and emitted compiler commands. Native runtime of the production function strengthens this scoped repair but cannot close356 or qualify the rest of Modelnet, helper spawning, root dependency provisioning, test_btx, or a release. There are many other direct Unix includes, some correctly guarded; do not turn this one measured file into an unbounded sweep.

This review does not verify native compilation/runtime of any candidate, or current public ownership beyond the coordinator's saved ownership snapshot. No posting authority is inferred. Original broader Windows finding credit remains repch1c, with JPP's complementary coverage reused.
