# Native Windows compiler fixtures

**Six generated compiler targets fail before/pass after; exact70f builds all seven maintained executables. Full Windows unit acceptance remains failed/incomplete.**

Code is unchanged commit `70f1886f1028b4d78b5689f4fd2f80ba1d195d96`, directly on Numair's requested `d522af52`. One commit changes six test CPPs only. Original authorship/license and repch1c/Jpp-matata credit are preserved. No publication-time test or build was repeated.

## Change and actual evidence

Keep the POSIX FIFO/permission cases on POSIX and retain shared safety assertions. Use Windows pipe calls for the existing Bash probe, native argv spawning for AHP API/Journey, and actual native-helper/refusal cases for Windows confinement/filesystem tests. POSIX bodies are preserved; product code is unchanged.

- [Two-target proof](two-target-proof.json): native42365244708 fails WAN mkfifo/AHPcomp pipes;42366423966 on08b2 compiles the same targets with identical generated commands/configuration. Arith control passes.
- [Four-target proof](four-target-proof.json): full42367406159 fails API/Journey/confine/fsjail;42373148335 on70f compiles those four under the same command table and links all seven executables in21.19s. [Independent compile review](compile-review.md).
- On70f, WAN and AHP-comp each pass six cases. The full unit campaign has other failures, a timeout and unselected cases. API/Journey originally stop at the separate configured-path defect; native helper cases are not reached in that campaign.
- [Later helper proof](helper-proof.json): source37472/run42413581374 passes API/Journey and both native-helper execution/cleanup cases, with identical six-file blobs, **plus #436 configured paths and adopted #433**. [Independent helper review](helper-review.md). This is not standalone70f runtime proof. The two added nonnative-helper refusal controls now pass on that exact saved37472 binary:16assertions,7.05s, expected rejection/no launch/root cleanup and no owned children left. No rebuild or passing-case repeat. [Raw controls and verification](refusal-controls/). Earlier reviews retain their dated scope.

## Prerequisites and limitations

**Runtime helper cases require #436's configured executable paths.** #436 is now incorporated into release9189; maintainers applying this six-file batch to swarm need that path correction there too. Compilation/link success itself is on exact70f. This does not close #356, qualify a full unit run or sign off a release. No new POSIX runtime, cl.exe or Windows11 desktop qualification.

Original raw compiler logs are in `compile/`; relevant case logs/XML retain their original suite or isolated-case context under `runtime70f/` and `runtime37472/`. [manifest.json](manifest.json) binds source/branch/blob/proof identities; [evidence-sha256.json](evidence-sha256.json) binds every payload. [six-fixture.patch](six-fixture.patch) is the exact six-file diff.

Actually executed CI entry points: [two-target](https://github.com/sunnyriverr/btx/actions/runs/42366423966), [four-target/full build](https://github.com/sunnyriverr/btx/actions/runs/42373148335), [helper path recovery](https://github.com/sunnyriverr/btx/actions/runs/42413581374). These were cache-dependent native workflows; this evidence package is not claimed as a fresh clean-build replay. The exact tested70f is the parent of the evidence commit and available as ordinary Git source. The saved5885object cache and original archives are preserved.
