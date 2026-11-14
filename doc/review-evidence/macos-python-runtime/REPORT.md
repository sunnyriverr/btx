# Focused Mac Python runtime packaging repair

## Verdict

Built a local packaging repair and proved **actual tar archives fail before and pass after**, reusing the saved native daemon. Nothing posted. Exact code/archives/results are recorded in repair-receipt.json and mac-python-runtime.patch.

The same disposable build input and currenta5d1637f packager produce baselinea8cb0e1c and repairedf27b2228. After unpacking under a different path containing spaces, and hiding the entire producer Python tree, the baseline wrapper exits127 for the missing external runtime. The repaired archive starts off by default, starts with SwapNet explicitly enabled, answers native regtest/SwapNet RPC, restarts with the same data and shuts down cleanly. No loader overrides or Python environment variables are supplied to consumers. automatic_spend_atoms=0 and wallet_loaded=false throughout; no financial operations or mining.

## Change and credit

One Mac-only integration hook plus bundle_macos_python_runtime.py and maintained tests. Reuses Jpp-matata's Linux678 import inventory/stdlib exclusions and retains original attribution/licences. The Mac implementation stages the linked CPython framework version, standard library, measured crypto packages and their native library closure. It retains licence metadata, flattens framework layout into real files/directories, rewrites copies to bounded loader-relative paths, strips build-host rpaths, re-signs edited copies then seals the framework/apps, checks architecture and signatures, and runs isolated imports from the staged interpreter. Mixed/unsupported Python layouts, wrong ABI/crypto pin, source symlink escapes, missing/escaping/ambiguous load paths and native collisions are refused. The existing source-binary launch, portability and archive checks remain enabled. Linux/Windows paths are untouched. Existing staged Qt dependencies and bounded executable-relative paths are preserved; actual Qt archive execution is not qualified by this fixture.

## Tests

- Native before: baseline archive fails default-off startup (exit127). Same preserved baseline result reused for final guard-only changes.
- Native after: default-off, enabled, three health polls per boot, enabled same-data restart and all three shutdowns pass. Actual RPC asserts regtest, embedded runtime, no loaded wallet and zero automatic spend.
- All69native images in extracted final archive verify dependency closure/signatures. Four native tamper probes reject bad signature, missing library, an existing target outside the archive, and Homebrew linkage. Probes are disposable copies, removed afterwards.
- Maintained bundle_macos_python_runtime_test.py:9passed, including ABI/import/architecture mismatch, collisions, descendant/root symlink escapes, normalized system paths, bounded app executable and worker-without-supported-runtime controls.
- Existing package_release_archive_test.py:58run,56passed,2skipped; do not report skips as passes.
- Bounded independent design/code review found source-validation gaps; each corrected and source-rechecked. Review performed no native execution. Final guard-only repack is byte-identical to native-qualifiedf27b2228; unchanged lifecycle evidence reused rather than repeated.

Commands and raw logs: build-archives.py, test-archives.py, test-native-gates.py, archive-execution.log, native-gates.log, maintained-controls.log and existing-packager-tests.log. Source-tested command: `python3 test/util/bundle_macos_python_runtime_test.py`. Native fixture requires the saved JPP binaries plus the pinned3.12.10 runtime/wheels from the existing task receipts; these are not a release distribution.

## Exact provenance and limits

Daemon originates in JPP43599161832 (64889922 mapped to70de5a45 plus CI), not currenta5d1637f. To satisfy the unmodified packager's clean-env launch gate on this machine without installing globalPython, only a disposable input copy's Python load command was adjusted to the owned producer framework and ad-hoc re-signed. Both before/after use that identical input. Original downloaded daemon remains2c623e18. This models an actual build-host dependency; consumers must work after that producer disappears, which the repaired archive demonstrates.

This is native macOS ARM64, ad-hoc signed, plain archive with wallet disabled/ModelNet off. Not a current-node rebuild, Qt/nativeGUI archive, Intel execution, hardened DeveloperID/notarization/Gatekeeper, otherOS, native swap settlement or release signoff. No tag, source branch, existing release download, wallet or production process changed. Broader S10 current-candidate package qualification remains open.

## Setup/review corrections and lessons

First packager invocation correctly rejected the old absolute framework path before staging. The disposable build-input adjustment preserved the gate; it did not bypass it. The first candidate missed canonical framework path spelling and yielded the same bad archive; actual extraction/relocation caught it, and detection now handles canonical Versions paths and fails closed for unsupported workers. Packaging-host systemPython stripped DYLD needed only for the uninstalled producer interpreter; the owned non-system orchestration interpreter resolved that fixture issue. Consumers never use these variables. Framework signing order and bytecode emission were corrected before qualification; the resource seal is made after nested signing and the import probe uses-B. Native all-image checking also exposed a legitimate existing CLI relative rpath; the validator now resolves/bounds it instead of weakening the check. These pilots/review catches are retained and are not extra product findings.

Reusable lesson: test the actual extracted archive with producer dependencies removed. Startup on the producer and a staged import alone miss the central distribution failure; signature/closure checks must run after the last edit and include both negative controls and existing non-Python callers.

## Finish and next

The requested focused repair/retained-binary archive qualification is complete locally. No outstanding concrete review finding. Next is the authorised publication decision for this focused source/test/evidence handoff, keeping the retained-binary limits explicit. A later exact-current-build/GUI release qualification remains separate and must not be claimed from this pass. Do not repeat valid tests merely while publication is held.

Publication attribution correction:678is authored by Jpp-matata; repch1c retains credit for earlier native SwapNet reports. Only the new module docstring changed, with executable AST identity verified and test/archive evidence reused.
