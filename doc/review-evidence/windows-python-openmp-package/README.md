# Windows Python/OpenMP command-line package — native evidence

**PASS:** the repaired actual ZIP supplies its own isolated Python and redistributable OpenMP runtimes. The stock archive fails launch; the Python-only intermediate still fails dependency closure. Final code: f7be3888f3c630cf1b853748510118b8f6873d19, based on `f40eb37a` (`swapnet-v2`).

## What changed

The packager accepts explicit `--windows-python-runtime` and `--windows-openmp-runtime` prepared directories. It stages the matching x64 Python embeddable runtime, cryptography/CFFI, transitive adjacent native dependencies and an isolated `python312._pth`. Unknown dependencies, wrong architecture, missing native cryptography, conflicting DLLs and multiple OpenMP copies are refused. No host runtime search is added.

Official LLVM 20.1.8 `libomp.dll` is preserved byte-for-byte under the linked `libomp140.x86_64.dll` compatibility filename, with its complete license. LLVM's own `OPENMP_MSVC_NAME_SCHEME` uses that name. Do not substitute Visual Studio's `debug_nonredist`. Four documented Windows OS DLLs used by the runtime are classified as system components; OpenMP and unknown DLLs remain subject to the existing gate.

## Actual before/after

- [Stock ZIP, run43661726579](https://github.com/sunnyriverr/btx/actions/runs/43661726579): assembly succeeds; extracted daemon fails launch with `0xC0000135`. The stock ZIP hash is `14830d7168ef8803e41a334cce550732294da73cef26af833d006060f4e207ee`. This control was reused.
- [Python-only archive, run43662359337](https://github.com/sunnyriverr/btx/actions/runs/43662359337): native Python/RPC/restart succeeds, but static closure correctly rejects five missing OpenMP dependencies. This negative result was preserved.
- [Final actual archive, run43663888605](https://github.com/sunnyriverr/btx/actions/runs/43663888605): `verify_release_btxd.py --archive` passes `windows-zmq-help+launch+cli+contents`; all native dependency problems are empty and all five executable version/help controls pass. Removing the bundled OpenMP DLL restores exactly the five expected refusals.
- SwapNet enabled RPC reports `in_process=true`, `automatic_spend_atoms="0"`, `wallet_loaded=false`. Same-datadir restart preserves this. Omitted flag returns the expected disabled error. Three RPC stops exit zero, with no forced cleanup.

## Runtime and isolation proof

All five saved executables' nine named OpenMP imports resolve; there are no ordinal imports. A real `__kmpc_fork_call` creates two native workers. Process module enumeration proves the daemon loads archive-local OpenMP and Python DLLs, including after restart. This is basic fork/join ABI verification, not every MatMul arithmetic path.

With deliberately hostile `PYTHONHOME` and `PYTHONPATH`, packaged Python reports isolated mode and bundled stdlib, cryptography, Rust and CFFI paths. The daemon also passes with these variables set. Strict Windows path containment was independently checked against the recorded native paths, without rerunning the passed lifecycle.

The producer validates SHA256 for official Python 3.12.10 x64, cryptography 46.0.4, CFFI 2.0.0, pycparser 2.23, LLVM 20.1.8 and its full license. Pip runs offline with `--no-index --no-deps --no-compile`. Input and prepared-file manifests are retained. The product helper accepts prepared inputs; provenance validation belongs to the producer recipe.

## Exact binary, archive and retention

Jpp-matata's native build [43599161832](https://github.com/Jpp-matata/btx/actions/runs/43599161832) supplied saved source `648899223329bd962146fb4e17fcfe3516075e17`, clang-cl 20.1.8. Daemon SHA256 stays `d8bd7dda90ab42e92882bd02005d919185a0cac4331af007a9ef78a0a9af16ab`; all saved manifest hashes were verified. No node recompilation.

Final ZIP: `284e5de24ed14c5eba78a2af4a347cddb247968fcd2dc6eabbfb284d6bff9918`, 46,800,927 bytes. Retained in fork CI artifact 14141910012 until 29 November 2026 01:37:38Z. Outer artifact and inner ZIP digests were verified independently. The archive's existing `w64-mingw32` filename does not imply MinGW testing: these are native clang-cl binaries.

Packaged OpenMP SHA256 `a12116ba72d1d6820407cf30be23da04ce79d6bb8a71a5ee71759c5a1faa6f1c`; full license SHA256 `fdad1758a9e1f9d5a81e18879b3406772115edc92c24bfa36b70c654f325e8e4`. Prepared and archive hashes match. Only one OpenMP DLL is shipped.

## Maintained tests and executed recipe

Run `python test/util/bundle_windows_python_runtime_test.py` for the maintained input/layout/dependency controls. Twelve cases passed natively with zero skips. Final source adds one duplicate-OpenMP-copy refusal: its new maintained case fails against the pre-guard helper and passes locally on Mac after the guard. This rejection-only post-native delta changes no bytes for the exact qualified pinned input; no native passing cases were repeated. The existing Windows ZIP/name unit also passes locally with its normal text fixture.

Exact executed CI wrapper: `c6afdaf0e5b8c62f6c708bc2f637d9152473cb4a`, `.github/workflows/windows-python-package.yml`, `contrib/devtools/windows-swapnet-runtime/probe.py` and `native_closure.py`. Copies of those executed entrypoints are in `recipe/`. The runner checks disk first, restores the saved artifact, prepares hash-verified inputs, assembles the ZIP with both runtime options, then invokes the archive gate and bounded native controls. `windows-runtime-inputs.json` is the producer lock; use that recipe rather than resolving wheels again. The new test is manually invoked by this recipe, not claimed as default CTest coverage.

See `source-identities.json` for final source hashes, `native/result.json` and raw logs for actual responses, and `native/actual-archive-files.json` for exact payload hashes. Internal source/evidence review found no blocker to these scoped claims; that is not a second platform execution.

## Limits

Hosted windows-2025 x64 using the saved JPP binary, not a current-f40 node build, full unit/functional run, installer/signature qualification, funded swap, Windows 11 consumer-machine run, full arithmetic qualification or release sign-off. ModelNet was disabled and no wallet was loaded in the daemon lifecycle. No production, wallet, consensus or automatic-spending changes.

## Primary references

- [LLVM 20.1.8 release](https://github.com/llvm/llvm-project/releases/tag/llvmorg-20.1.8), [naming source](https://raw.githubusercontent.com/llvm/llvm-project/llvmorg-20.1.8/openmp/runtime/CMakeLists.txt), [full license](https://raw.githubusercontent.com/llvm/llvm-project/llvmorg-20.1.8/openmp/LICENSE.TXT).
- [Python embeddable distribution](https://docs.python.org/3.12/using/windows.html#the-embeddable-package).
- [Microsoft OpenMP distribution restriction](https://learn.microsoft.com/en-us/cpp/build/reference/openmp-enable-openmp-2-0-support?view=msvc-170).
- System DLLs: [Microsoft Cryptographic Primitives](https://csrc.nist.gov/CSRC/media/projects/cryptographic-module-validation-program/documents/security-policies/140sp4825.pdf), [Propsys](https://learn.microsoft.com/en-us/windows/desktop/api/propsys/nf-propsys-psgetpropertykeyfromname), [Cabinet](https://learn.microsoft.com/en-us/windows/win32/api/fdi/nf-fdi-fdicreate), [Msi](https://learn.microsoft.com/en-us/windows/win32/api/msiquery/nf-msiquery-msiopendatabasea).
