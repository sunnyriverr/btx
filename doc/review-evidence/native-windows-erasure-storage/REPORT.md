# Native Windows erasure-storage repair — PR396 evidence

**PASS, scoped: the production source builds with native cl and clang-cl, and the real reconstruction operation passes18 storage/control checks on each.** A header-only intermediate compiles but fails byte preservation on both, proving the binary-mode change is necessary.

## Code and provenance

Local branch `codex/native-erasure-storage`, commit `b6e3062e05887afdf1ad3fa5c2c2d8ea7ba773d4`, parent `3c542cd6800755a891cd3ffafd839fd682e7ec40` (PR396 prerequisite on acceptedab1). Two files: `src/modelnet/erasure_store.cpp` and standalone `test/util/erasure_store_file_tests.cpp`. Shared index and HEAD were preserved; see `branch-receipt.json`. The fixture's packaged filename differs, its executed bytes do not.

The change splits Windows io.h from POSIX unistd.h, includes standard I/O declarations explicitly and adds Windows `_O_BINARY` to the existing descriptor flags. Exclusive creation, verification, reconstruction, flush/close, cleanup and rename handling are retained. Existing0644 mode worked in the native runtime and was not changed. Original broader Windows finding credit: repch1c in356; JPP's complementary coverage was reused.

## Actual results

[Native run41740815956](https://github.com/sunnyriverr/btx/actions/runs/41740815956), CI `772bb25a7d0d7c73a988c10d94e339903848ee3d`: Windows Server2025 x64, SDK10.0.26100.0, toolset14.51.36231, cl19.51.36260 and clang-cl20.1.8. Explicit C++20 component flags use static CRT `/MT`, `/Gy`, `/OPT:REF` and the396 forced header. The final fixture is identical across variants.

| Gate | cl | clang-cl |
| --- | --- | --- |
| Original source plus396 | build fails, missing unistd.h | same |
| Header-only intermediate | builds; runtime fails binary byte equality | same |
| Combined candidate | builds and18 runtime checks pass | same |

Final native Mac/M4 controls with Apple clang17: original and candidate both build and pass18 checks. This includes existing POSIX destination replacement. `mac-final/` holds actual final records. The pilot missing `univalue_get.cpp` caused a harness link failure; adding the actual fourth UniValue source corrected it. It was not a product defect. Retained pilots are not final qualification.

The fixture calls real RepairStripeFromFiles, codec, reconstructability, SHA-384, types, I/O executor and complete UniValue dependencies:11 real translation units and29 source/header inputs, no stubs. Two256-byte systematic shards contain every byte, including LF/CRLF/NUL/control-Z; the512-byte output is compared exactly. Controls cover invalid hashes, duplicate positions, short/missing shards, temp-directory collision, rename refusal and temp cleanup, and a subsequent healthy repair. Final fixture removal succeeds.

`artifact-verification.json` verifies174 native source hashes,12 log hashes, candidate/test/runner identity and the executed remote runner against local bytes. `result.json` records commands/results; `closure.json` records inputs. Independent design and artifact review PASS is in `review/FINAL.md`. Native executable files/hashes were not retained; exact CI/source identity, commands and verified logs support this execution record, not binary-distribution qualification. Mac binaries remain in the owned result directory. The cl `/Bv` version query exits2 without an input; named compile/runtime commands determine the verdict.

## Scope and preserved differences

Windows existing-destination rename remains refused; POSIX replacement remains supported. Both controls pass. Ordinary stale tmp files are removed before exclusive creation; the directory-collision case tests actual refusal. Existing Windows O_NOFOLLOW=0 is unchanged; no new symlink/reparse guarantee is claimed. Flush succeeds through the existing commit adapter, with no power-loss or injected write/fsync/close failure qualification.

These are actual implementation component builds, not root-generated flags, full Modelnet linkage/helper startup, a native node, test_btx or release qualification. OpenSSL>=3.5 setup and other production/unit portability blockers remain. Native MinGW runtime and Linux execution are unverified. Inputs use systematic positions0/1; arbitrary parity recovery and concurrency are outside this test. Validation/codec/manifest rules are unchanged.

`preflight.json` rechecked all4openPRs,356replies and acceptedab1 before dispatch. Earlier ownership snapshots checked named peers' public Actions/events. No competing public fix was found; private work cannot be excluded. JPP's MinGW campaign was not duplicated.

## Delivery

This tested delta is consolidated into [PR396](https://github.com/btxchain/btx/pull/396), preserving the original header/CMake repair and credit. Full native356acceptance is still outstanding. See README.md for the standalone reproduction entry point. The prior failed Mac harness pilot remains an explicitly disclosed setup failure; it is not part of the final qualification.
