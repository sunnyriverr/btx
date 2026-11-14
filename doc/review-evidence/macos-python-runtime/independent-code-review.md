# Independent Mac Python bundler code review

15 November 2026. Read-only bounded source review of `bundle_macos_python_runtime.py` (SHA256 `bb11a1a4a36d51740cd483924fd6e4640cbc785dd566bf9a1ac55efaa6ff9e1d`) and its `package_release_archive.py` integration. No test/build/network/native execution or source mutation by this reviewer. Parent owns native archive evidence. Findings below concern the inspected source snapshot; subsequent fixes need a delta check.

## Concrete findings requiring disposition

### P2 — Existing Qt dependency spellings are unsupported

The hook runs for every Mac archive and `entry_mapping` explicitly includes Python-linked Qt executables. Its dependency walk therefore visits each Qt entrypoint's non-system dependencies, not just Python. `resolve()` supports `@loader_path`, `@rpath` (with loader-relative/absolute rpaths only) and absolute paths, but rejects `@executable_path`. A deployed Qt app using the normal `@executable_path/../Frameworks/...` dependency or that spelling in an LC_RPATH now fails `bundle_macos_python` with unsupported/unresolvable dependency despite the existing Qt deploy path being otherwise valid. This is a product compatibility issue in the shared Mac packager hook, not evidence from the daemon-only native pass.

Disposition: resolve already-staged app dependencies against the correct app executable, require the resolution stay within the release tree, and preserve existing copies/signatures, or explicitly reject/limit a Python-linked GUI scope instead of implying it is covered. A maintained Qt-style relative-load control is needed. Do not add an unbounded cwd or developer-prefix fallback.

### P2 — One supported Mach-O container is silently skipped

`MAGIC` has seven forms and omits the little-endian FAT64 magic `b'\xbf\xba\xfe\xca'` which the existing verifier's `MACHO_FAT_MAGICS` recognizes. `macho()` returns false for that supported binary/library container, so it is omitted from the runtime/dependency/signature worklist. In the entrypoint case the linked list can become empty and the bundler returns no runtime; in a copied native module case the relative-load transformation and signature/closure checks are skipped. Use the existing verifier's complete magic/classification rather than maintaining a partial second set, and cover that container in a maintained classification control.

### P2 — System-library exception is based on unnormalized spelling

Both `verify_closure` and the dependency walk exempt a dependency merely because its raw string starts with `/usr/lib/` or `/System/Library/`. Thus `/usr/lib/../local/lib/example.dylib` is treated as system even though normalization resolves outside the allowed system roots. `verify_macos_portable` only checks Homebrew spelling/signatures, so it does not repair that exemption. The archive verifier separately normalizes spellings, but the bundler must not claim closure passed while skipping such a dependency. Normalize absolute names before bounded system-prefix checks; preserve strict component boundaries. Add a refusal/control for a dot-segment escape rather than relaxing the archive gate.

## Earlier concerns resolved in the live code

The original no-link branch now checks `embeds_swapnet` and refuses a worker with no supported shared framework; it no longer silently emits a runtime-free archive for that marker. `copy_package` now rejects directory and escaping third-party symlinks before the inherited tree copy. Those initial design-review concerns are resolved in the inspected source.

## Other inspected invariants

The inspected code requires one linked framework major/minor, host import success, the repository cryptography pin, no conflicting pre-existing runtime destination, relative staged load closure and post-edit signatures. The staged interpreter probe uses no DYLD/PYTHON override and checks prefix/module origins under the release root. App signing is after inner-file edits, with the Python framework seal last. No additional concrete signing-order defect was established by source read; the parent's actual archive/signature result remains decisive.

The archive native pass cannot attest Qt deployment or another architecture container unless exercised. Retained70de-derived inputs remain different from current integration binaries. No source-review conclusion here expands those execution claims.


## Final delta recheck — 15 November 2026

Read only the change addressing the findings above and the new maintained test definitions. Live bundler SHA256 `84fc7b4f39599ffad6d231e770fa1593df1c020f1bda5dd66320a9e147a5d830`. No test/build/native execution or source edits by this reviewer.

- **System-path finding resolved:** `system_load` normalizes absolute paths before checking component-bounded `/usr/lib/` and `/System/Library/` prefixes. Both the dependency walk and final closure validation call it. The added definitions distinguish real system paths from dot-segment escapes.
- **FAT64 finding resolved:** MAGIC now contains all eight thin/fat byte orders represented by the existing verifier, including `b'\xbf\xba\xfe\xca'`.
- **Qt spelling finding resolved in the inspected source:** `resolve` now handles `@executable_path` directly and inside rpaths. `executable_directory` locates the nearest app's Info.plist executable and requires it exist within that app. Already staged non-Python dependencies remain at their bounded current locations, are referenced from edited entrypoints relatively, and retain their existing library signatures/rpaths instead of being recopied and rewritten. Edited app executables are still re-sealed after inner changes. The added tests cover app executable context and an escaping plist value. This is source/definition review, not a claim that a native Qt archive was run.

All three findings in this review are disposed in this live snapshot. No additional concrete blocker was established by the bounded delta. Parent-owned final archive byte identity, native dependency/signature gates and scope disclosures remain required; the earlier report is retained as review history rather than removed.


## Final closure-validator delta recheck — 15 November 2026

Read only the revised `verify_closure` path-resolution logic and its existing `system_load`/`executable_directory` dependencies. Bundler SHA256 `661ce960ffad19adbeab1e89bfe5eb8c79d328375cb2d1fa3802fa97d807d165`. No tests, source changes or native execution by this reviewer.

The correction preserves existing, bounded relative LC_RPATH directories instead of rejecting every non-system search path. `@loader_path` and `@executable_path` directories must exist and resolve within the archive. An `@rpath/...` load must resolve to exactly one existing canonical target among those relative search directories; missing or distinct ambiguous targets refuse, and the final target must remain within the archive. Direct relative dependencies receive the same existence/root check. System loads retain the previously reviewed normalized exception. App executable context remains bounded by the existing plist/executable check.

No concrete blocker was established in this bounded validation-only delta. This is not removal of the dependency/signature gates: `verify_macos_portable` still runs first, paths are resolved and bounded, and unresolved/escaping/ambiguous loads fail. The parent's reported native all-image gate and final repack byte identity must establish the actual artifact claim; I have not rerun them or independently checked the archive hash. If the final archive is byte-identical to the already natively qualified archive, this validator-only correction does not itself require another identical positive daemon lifecycle run. Retain final validator/unit evidence separately from reused native artifact evidence.


## Architecture, caching and distribution-metadata delta — 15 November 2026

Inspected only these source additions, bundler SHA256 `aa52beec95907a3b3fad4edd50cb6293b2f0151f11d1ed8c961968de4f67273c`. No tests, build or native execution by this reviewer.

The normal Mac staging call passes the platform triple's architecture. `verify_architectures` refuses unsupported names and requires the expected arm64/x86_64 slice in each touched Mach-O before final dependency closure. Cached fixed helper imports preserve the prior semantics without repeated loading. Distribution metadata selection matches normalized imported root names, with `_cffi_backend` attributed to `cffi`; the selected metadata preserves available licences/attribution alongside the copied module roots. Parent appropriately reruns the changed archive because metadata changes resource seals/bytes.

**One narrow copy-boundary finding remains in this snapshot:** a `*.dist-info` directory can itself be a symlink. The loop discovers it through `parent.glob`, and `copy_package` checks descendant symlinks but not `source.is_symlink()`. A root alias to a directory outside the scanned site-packages parent is therefore followed by inherited `_copy_tree`, unlike the intended bounded-source rule. Reject a symlinked copy root (or require its resolved path remain within the scanned parent) before tree copying. A test of root alias refusal complements the existing descendant-symlink controls. This requires no new runtime scenario when the actual archive's selected metadata contains no such alias and its bytes are unchanged by the guard correction.

No additional concrete architecture/caching blocker was established. This review does not attest the parent's final archive execution, hash or licences beyond the inspected selection/copy logic.


## Root-alias disposition — 15 November 2026

Read-only guard/test-definition recheck at bundler SHA256 `6afba4feb0be0cde6457a689ca616585a10ec56067316141d9934b443e125b23`. `copy_package` now refuses `source.is_symlink()` before either directory handling or the inherited copy, and the maintained definition includes an `alias.dist-info` root alias that must refuse before copying. The last recorded finding is resolved in this source. No additional scope examined and no tests run by this reviewer. Parent-reported nine maintained passes and final archive byte-identity remain the parent's execution evidence, not this source-review result.
