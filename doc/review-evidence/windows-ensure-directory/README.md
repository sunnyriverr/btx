# Windows capability ensure directory compatibility — qualified, unpublished

**Exact generated object command: stock61f13b88 FAIL; candidate PASS. Focused Windows and Mac directory controls pass. Full unit/ensure workflow qualification remains incomplete.**

## Change and reason

Keep the existing POSIX EnsurePrivateDir body byte-for-byte. Under_WIN32, call existing modelnet::security::EnsurePrivateDirectory and translate its typed refusal to the existing false/error return. Include security_v2/common.h only on Windows. No new ACL implementation or permissive fallback; no CMake change. bitcoin_modelnet already defines securityv2 and links bitcoin_model_security PUBLIC unconditionally in the inspected configuration.

The shared Windows helper creates a protected owner/SYSTEM-only directory, rejects reparse points and checks ownership/ACL on existing directories. Windows broad-access directories are refused rather than silently trusted. A healthy existing private directory remains usable. POSIX ownership, lstat, mode0700 tightening and error paths are unchanged. Patch: ensure-directory.patch; candidate: capability_ensure.fixed.cpp.

## Verified evidence

- Baseline43711509525 on exact61f13b8870ed98c7b10db2e32c04fb647023f4ef failed capability_ensure.cpp at131mkdir,136S_ISDIR/geteuid. No new baseline fullbuild repeated.
- Candidate43712374900, same CMake-generated command dictionary compared to the baseline configure artifact, exit0/12.78s. No compiler flags changed. Only that product object compiled; full unit target not resumed.
- NativeWindows wrapper harness links the existing verified bitcoin_model_security dependency and exercises the extracted candidate function. Diagnostic controls43712765925 passed12 assertions, including fixture setup: private creation/reopen, ordinary-file refusal, explicit broad-ACL refusal, junction and junction-ancestor refusal, healthy retry and retained file bytes.
- Focused macOS extracted-function controls passed8 checks: create/reopen, file refusal, mode tightening to0700, symlink refusal, retry and existing bytes. The POSIX body is byte-identical; this is not a fullPOSIXproject rebuild or suite.
- A new Windows cleanup-only control43712999067 reproduced open-stream removal refusal and confirmed closing it permits complete cleanup. Original harness correction is explicit ifstream.close before remove_all. No repeat product compile or repeated directory-behavior run was needed for this cleanup control.

## Fixture errors and interpretation

First native harness43712374900 exited3221226505 without buffered diagnostics. Added exception reporting and flush in43712765925 exposed that all12 behavior/setup assertions passed, followed by cleanup failure because ifstream remained open. The product did not cause that cleanup failure. Fixed harness stream lifetime; minimal native cleanup control passes. This is a composite qualified result, not a claim that either earlier whole workflow was green. Logs preserved in ensure-evidence.zip, ensure-controls-evidence.zip, ensure-cleanup-evidence.zip; each artifact digest checked locally.

## Limits

Not a live ensurebtxcapability RPC journey or fullWindowsunit link/run. No freshfullPOSIXbuild, second-user/SYSTEM ownership-change test, FAT filesystem, exhaustiveACL/symlinkrace test or production operation. Windows private-directory checks are reused from an existing linked implementation; no broader securityfix claim. No upstream publication. Previously stopped investigations are untouched.

## Preservation and next

Original unit-progress cache10552981827 remains unchanged. Candidate cache10553232364 actualAPI key **btx-ensure-candidate-43712374900**,496704500compressedbytes,12934files. Its manifestSHA098f12ce453d1c32319fa9e4a1712caea99204635d18ded151a391d0823e53f6 was independently restored and allfiles/source hashes verified in43712765925. It contains HEAD61f13b88 with a **dirty, explicitly recorded candidate source file** and compiled candidate object; it is not a stock61checkpoint. Apply/verify the exact candidate patch before sourcecatalog validation on laterrestore. Generic retention receipt's suggested release17key is stale; actualworkflow/cacheAPI key above governs. No originalcache overwritten.

Next: final focusedpatch/handoff review, then publish compatibility correction with repch1c credited for the underlying private-directory fix and existing security-helper authorship preserved, when authorized. After incorporation/candidate selection, resume remaining unit target from a source-matched checkpoint. No duplicate objectbefore/after, fullsuite or passingCLI tests needed for this handoff.


## Attribution and provenance

Underlying directory protection is repch1c's PR720, incorporated as7a1360d5 with original authorship. This portability patch invokes the existing modelnet::security helper; its existing authorship is not claimed here. It adds no ACL reimplementation or production-policy weakening.

Baseline native build https://github.com/sunnyriverr/btx/actions/runs/43711509525
Candidate object https://github.com/sunnyriverr/btx/actions/runs/43712374900
Windows extracted controls https://github.com/sunnyriverr/btx/actions/runs/43712765925
Cleanup-only confirmation https://github.com/sunnyriverr/btx/actions/runs/43712999067

AI-assisted preparation and review. The candidate native workflow failed at harness cleanup after successful object compilation; the later control run exposes all12passing assertions and that cleanupfailure. Do not interpret its red badge as productfailure or its12checks as fullRPCqualification. The Mac checks ran an extracted unchangedPOSIXfunction, not a fullBTXbinary.
