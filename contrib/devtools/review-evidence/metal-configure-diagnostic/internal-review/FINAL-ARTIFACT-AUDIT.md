# Final actual-code and evidence audit

**PASS for the focused Mac CLT configure-diagnostic handoff**, on exact current swarm `cbf65894e6d61084527cd93e913a00c6794418dd`. No unresolved material correctness or evidence-claim issue found. This is an independent agent's source/artifact audit of the executor's results, not a second native run or human review.

## Sealed inputs

- Approved patch remains SHA-256 `d77b5adeadb739efa101c55a2e6e9625ce6db8648e7e0f34baf7596e81e2dcf3`.
- Reconstructed both patched files in memory from their exact target Git blobs and unified hunks; they match retained actual product bytes: `src/CMakeLists.txt` SHA-256 `396ea4cbb5fcc099d090bd81bf32a71d8a4a413060779ed319c0fc232f0570f9`, `doc/build-osx.md` SHA-256 `fee459a08fcc64d5c5e67c7b2ae045bb48f505f97b9de20bcb5fc9d494cb830e`.
- Verified the final 81-artifact catalog in full. Final `SHA256SUMS` SHA-256 is `aef313bdd2cdbd964126f9268fb6682c5f2695f4843408743503d75ba758e203`; final `REPORT.md` is `59cb2b4c5392b57650979e7c7cf673465ecb87352e7657bad8fd64a7c76585df`.
- Final executed candidate entry-point hash is `685baefc7c3570de43ff62ce150d656e7fc5378d6fa9a4788d5447dd58f6a56e`, matching the retained script and summary. Read the actual script and dispatcher, not just the report.
- All 14,271 manifest paths and base-blob identities match the immutable target Git tree. Manifest deltas are the two approved product files and the disclosed `src/clientversion.cpp` archive export substitution. Its retained original bytes match the Git blob; the source marker is a Git commit-ID export substitution. No shared dirty checkout is presented as the tested source.

## Actual source and platform checks

The applied patch is exactly the source-approved design. The new required check is inside the existing Apple+Metal/precompile-ON/xcrun-found path; basic compile and link use the same SDK/default-language operation as required builds. Both new stages have quoted paths, fresh output checks and 30-second timeouts. Result strings, missing outputs and stage diagnostics are handled correctly. The optional Metal 4 check's timeout/failure behavior is unchanged. All six mandatory build commands remain. The moved docs note complements the open #344 setup rewrite rather than adding another paragraph at its insertion site.

Caches agree across native baseline/candidate and controls on Release, Unix Makefiles, CLT C/C++ compilers, `/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk`, `/opt/homebrew`, static-libomp include selection, serial-prover OFF, daemon ON, default ZMQ ON, and the disabled Modelnet/wallet/GUI/tests/bench/extra-tool profile. Objective-C++ is absent only in Metal OFF, as expected from the original outer branch. These are actual full-project configurations with controlled xcrun substitution in named fixture cases, not an extracted replacement CMake block.

## Observations and sensitivity

Read native tool-selection logs, configure receipts/logs, required-target failure, all final case receipts, probe identities, recorded tool invocations, target graphs and backend flags.

- Native macOS 26.5.1 arm64 / AppleClang 17 / CMake 4.4.3 baseline configures successfully with missing `metal`/`metallib`; building only the required MatMul library target fails because actual xcrun cannot find `metal`.
- Identical native candidate ON configuration fails early at basic compilation, result 72, with native missing-tool text and explicit setup/OFF guidance. Native OFF configures successfully with no probe artifacts or metallib targets; this does not test runtime compiler availability.
- Recording positive basic tools create fresh text AIR/library outputs; trace order is default compile, metallib link, then optional Metal 4 compile failure. Six required targets/basic definitions survive, while optional Metal 4 targets/definitions do not.
- Recording link failure follows a successful basic compile and fails specifically at metallib linking with exactly two calls. This distinguishes a broken compile-only/metal-only guard from the approved implementation.
- Empty cached dispatcher produces the existing no-xcrun fallback without probes/targets. It is injected CMake selection coverage, not real Apple PATH discovery. Metal OFF also configures without invoking the rejecting dispatcher or generating probes/targets.

The supported handoff claim is the native missing-tool failure moving earlier, with focused branch controls. Actual successful Metal compilation/linking, full Xcode, Metal 4 capability, runtime Metal service, GPU execution, full node linking, release packaging and other platforms remain unqualified.

## Recipe, pilots and cleanup

The reproduction document describes a fresh two-phase entry point, exact source and prerequisites. Actual provenance is narrower than a clean replay of that final unchanged recipe: baseline used an earlier observation-only runner; the final candidate invocation reused its completed native ON observation and ran the remaining controls. Report and summary disclose this. Do not relabel it a separately executed clean final-matrix replay. No new repeated run is needed to substantiate the current configure claim.

Archive compatibility/symlink pilots, baseline summary-padding assertion correction, interrupted pre-Metal monitor pilot, and native-error line-wrapping correction are retained honestly. None changes the product/configuration or is counted as another completed product failure/pass. One minor final wording correction changed “SDK/tools/library hashes” to “Selected SDK and exact tool/library hashes”; the final report/catalog were read back and all hashes reverified without repeating tests.

Cleanup receipt and filesystem inspection agree: owned full source and every build directory are gone; actual product files, logs and identities remain. A read-only process check found no owned execution commands. Executor reports about 16 MiB retained and 2.04 GiB free; completed-run sampled minima/peaks meet the existing 1.25 GiB/350 MiB bounds. No reviewer runtime/build/cache/VM resource was acquired. Reviewer output reservation is released for coordinator integration and the already-authorized next handoff decision; no new test or publication is initiated by this audit.
