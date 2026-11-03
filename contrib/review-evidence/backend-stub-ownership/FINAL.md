# Independent final review

Reviewer: delegated `backend_linkage_review`, 2026-11-03. Review-only checks; no compiler, linker, runtime, GPU, VM or publication execution by reviewer. Read `REPORT.md`, `candidate.patch`, `run_checks.py`, `identities.json`, `results.json`, `summary.json`, `build-graph-check.json`, exact source/candidate files, and recorded failure/symbol logs.

Verdict: **PASS for the bounded source-ownership repair and recorded macOS component evidence**. The requested report wording correction is resolved and verified. Ready for a scoped handoff. This is internal independent artifact review, not independent Windows or GPU execution.

## Code and identities

The patch removes precisely the nine redundant CUDA/Metal/HIP generic entry definitions and their guards, leaving the Ascend implementations and platform linkage macro unchanged. The other four changed files are comment-only; CMake commands and source selection are unchanged. Per-vendor implementations/stubs, including HIP's output clearing and BMX4 adapter, remain intact. The repair resolves redundant ownership without broadening runtime behavior or changing GPU selection.

All 64 retained baseline files match immutable `cbf65894` git objects. The five baseline/candidate hashes and patch hash match `identities.json`; the current harness hash matches both that file and `summary.json` (`96739dd29e9c94da3f5f84f128f25b477026ea79bf71f6629c05846e696d2eeb`). Source/candidate differences are confined to the five patch files. The real header closure is used; no substitute CBlockHeader/uint256 ABI is present.

## Observation and oracle

`results.json` has 104 commands. Its eight nonzero outcomes are exactly the seven expected duplicate-symbol links and the deliberate wrong-provider runtime rejection. Each of the four all-disabled strong-branch baseline link logs reports nine duplicate symbols; each one-enabled baseline log reports six remaining disabled-vendor duplicates. Candidate links/runs and native weak legitimate controls succeeded. Recorded post-command free disk is at least 1,623,257,088 bytes, above the 1.25 GiB reserve.

The wrapper deliberately defines `_MSC_VER`/`__MINGW32__` only after native parsing of the headers that the actual generic TU includes. It therefore tests that TU's real conditional branch without pretending the host has Windows headers or ABI. Recorded `nm` output confirms baseline weak definitions under the native branch, strong definitions under the emulated branch, and only the three Ascend definitions in the candidate. The harness's strong check rejects weak externals; its exact count assertion and reviewed symbol logs provide complementary evidence.

The harness calls all twelve generic dispatcher-facing entries and the distinct vendor-only surfaces that could otherwise be hidden by archive extraction. Direct-object and force-loaded archive checks expose duplicate ownership independently of ordinary extraction. Candidate ordinary archives also link/run; lack of an ordinary strong-baseline result is disclosed and does not invalidate the direct-object ownership proof. It prevents claiming a complete reproduction of Windows node archive extraction, which the report expressly avoids.

One-enabled provider cases select each vendor's three synthetic marker functions and retain Ascend with both Ascend/CANN defines present. The Metal wrong-provider mutation is rejected at runtime on the first provider return-value assertion. This demonstrates that mere successful linkage is insufficient for a passing enabled-provider result. These controls exercise ABI/provider selection, not device computation or the real dispatch algorithm.

The CMake assertions match inspected source branches, including HIP's separate archive and the actual `APPLE AND BTX_ENABLE_METAL` condition. They are source checks, not CMake evaluation. Unchanged build commands, the source audit and the component tests together support this small deletion; no full GPU configure is implied.

## Report correction and limits

Resolved: the report now precisely describes scalar digest first-byte preservation, batch digest-vector size, and complete seeded payload/payload-vector checks, and explicitly excludes remaining digest bytes and retained batch digest contents. HIP batch/BMX4 output-vector clearing is fully checked. The corrected report was reread; no additional experiment was needed. The actual unchanged stub bodies have also been reviewed.

Native Windows clang-cl/MinGW compilation/linkage, COFF archive behavior, native Linux, actual enabled GPU build/runtime, full-node link and consensus behavior remain unverified. The report preserves these distinctions, credits repch1c's original Windows observation and does not claim this fixes unrelated issue #356 blockers. No extra test campaign is needed for the scoped local claim.

Reviewer output remains confined to `review/`. No processes or mutable build resources were acquired by this reviewer. Parent owns the final receipt/ledger and any subsequently authorized delivery. All reviewer actions are complete; reviewer resources are released.
