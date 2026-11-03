# Early Metal precompile diagnostic

Product code `1ed289e06387b0299eb0b76da5a16ed8fd5e1a60`, based on current `btx-035/swarm` at `cbf65894`. The concrete request is [repch1c's review on #344](https://github.com/btxchain/btx/pull/344#issuecomment-6542655967). This is a build-system follow-up, separate from vonlevo's documentation rewrite.

- Real macOS CLT baseline: full focused-project configure succeeds, then the required metallib target fails because xcrun cannot find metal.
- Patched identical selection: configure fails early with a stage-specific setup/runtime-option hint. Real precompile-OFF configuration still succeeds.
- Recording-tool fixtures preserve basic success with unsupported optionalMetal4; missing metallib is rejected at linking. Empty-dispatcher and Metal-OFF controls keep their prior fallbacks without tool calls.
- [Report/limits](execution/REPORT.md), [source patch](execution/metal-configure.patch), [actual cases](execution/summary.json), [reproduction](execution/REPRODUCE.md), [artifact audit](internal-review/FINAL-ARTIFACT-AUDIT.md).

The two-phase reproducer regenerates a private full source tree from exact Git objects and requires already installed normal Mac build dependencies; it performs no installation. Source/header/archive-extraction, summary-format and resource-monitor pilots are disclosed. The native baseline ran an earlier observation-only driver revision; the final candidate invocation resumed its completed native observation and ran the remaining controls. Do not call this a separate clean replay of an unchanged final matrix.

No full Xcode/native Metal-positive build, actual Metal4/compiler-service/GPU execution, full-node linkage, release profile or other platform is qualified. Controlled AIR/metallib outputs are text fixtures. Modelnet/wallet/GUI/tests/tools were disabled, daemon remained ON, ZMQ stayed default ON and actual static libomp was used without a serial override. No monetary or runtime-validation rule changes.

Only selected textual evidence is included: no binaries, private keys, node data or build cache. The full14,271-file source assembly catalog remains local, identified by hash in full-source-catalog.json. Original/published normalization hashes are retained; user paths are redacted. SHA256SUMS describes only this public selection, not the executor's broader81-file catalog. Internal review did not independently execute the tests. Patch applicability to344head is a Git source check only, not another native qualification.
