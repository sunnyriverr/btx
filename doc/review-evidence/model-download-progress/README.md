# Model-scoped download progress — Linux qualification

**Same maintained cases fail on release `23ee567e` and pass with this patch.** An unrelated stored model A inflated B's download counter, percentage, cumulative rate and ETA. This changes reporting only; content admission, storage limits and transfer policy are unchanged.

## Result

[Executed run44204471443](https://github.com/sunnyriverr/btx/actions/runs/44204471443), recipe `abcf47b550672015e02e5022af81740ad914bea3`, current base `23ee567ea8a2d9cad8ca3264f8793e8371b3eb93`. Ubuntu22.04 x86_64 container on an Ubuntu24.04 runner, GCC11.4.0, existing Release build configuration, real helper/PQ1/loopback.

|Case|B present|Baseline reported|Patched reported|Patched percent|
|---|---:|---:|---:|---:|
|Single-file|4,194,304|37,748,811 (100%)|4,194,304|24%|
|Two-file|4,194,304|37,748,811 (100%)|4,194,304|19%|

The single-file live resumed sample has the same distinction while requests are inflight. Final patched counters equal B's complete16,777,291 and20,971,668bytes. Both phases complete exact original file hashes, preserve the unrelated A and B's saved pieces through a clean helper restart; all12helper starts exit0, runtime directories removed.

The candidate helper builds in52Ninjaactions/407s. The baseline binary and23 previously executed `modelnet_file_stream_tests` cases from [run44198067492](https://github.com/sunnyriverr/btx/actions/runs/44198067492) are reused after15stream/store source-closure matches. Those are historical unchanged controls, **not a rebuilt current aggregate test_btx or a rerun on this candidate**. The prior run's native classifier failed and is not counted as the final before/after proof.

## Review entry points

- [Exact product+maintained regression patch](candidate.patch), [file hashes](changes.json).
- [Baseline native observations](records/baseline-native/result.json), [candidate observations](records/candidate-native/result.json), [build/phase timings and exact source closure](records/qualification.json).
- [Summary, binary/artifact hashes and limitations](qualification-summary.json), [internal read-only audit](review.json).
- [Executed native adapter](recipe/native.py), [build controller](recipe/qualify.py), [workflow](recipe/workflow.yml), [manifest](manifest.json). Large raw RPC traces/XML are losslessly gzip-compressed; manifest records compressed and original hashes.

## Execution and reproduction

The named CI job executed `python3 -B proposal/qualify.py` in the pinned Ubuntu22.04 container. It restored the verified build cache, admitted the current baseline binary, overlaid exact current tracked source, installed the **same** maintained test file in both phases, then ran:

```sh
python3 -B proposal/native.py --helper baseline-helper/bin/btx-modeld --sha256 28d7ecb6c611e5676d85de7a64038bc7d07cd0b6b2fb2606390d5e6405838ad2 --expect baseline --out records/baseline-native
ninja -j2 btx-modeld
python3 -B proposal/native.py --helper gui-pilot-runtime/qtbuild/bin/btx-modeld --sha256 a56c7e2f6fd02acb055ba46983609c2b77bcd887b1d65fa96fe131634eb93ac2 --expect candidate --out records/candidate-native
```

The adapter invokes the maintained `progress` and `progress_multi` cases from `test/functional/feature_modelnet_retrieve_regressions.py`; it does not launch a node or run the entire functional script/framework. It isolates helper HOME, checks executable identity/pacing, retains raw RPC and checks normal process exit. Baseline classification accepts only the measured A-contaminated counter after legitimate integrity/restart controls complete; arbitrary failures remain failures. Fourteen offline validator checks include negative cases.

The recipe records retained absolute build paths and expiring artifact prerequisites. It is the actual executed cached-build recipe, not a clean-build reproducibility claim; future execution needs a compatible cache or normal source build. Binary and current helper checkpoint artifacts are separate from test records and expire2December2026; hashes remain in the summary.

## Limits

No actual Atlas window, full node, full current test_btx/first-run suite, native Mac/Windows, WAN or release qualification. Stream-entry was observed; a targeted current-helper partial-Finish failure was not injected. The23unchanged hydration controls cover their recorded component scope only. Saved pieces are preserved, not proof that no piece is retransmitted. Intermediate concurrent external writers to the same artifact are not qualified; final install rebases once. Rate remains cumulative model-local stored bytes divided by job age, not newly transferred wire throughput.

## Attribution

The repair and added cases are new work by sunnyriverr. They preserve the existing retrieval implementation and repch1c's worker-lifetime behavior; adopted cancellation-save #823 is retained. No code or reviewer credit is reassigned.
