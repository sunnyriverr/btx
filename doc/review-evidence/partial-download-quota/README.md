# Partial model download quota recovery

The same Linux helper workflow failed with disk quota before the fix and completed at the original 72 MiB cap after it. The 71,303,243-byte model matched the source and manifest SHA-384, and its saved pieces were preserved. Fresh downloads completed at 72 MiB. An independent 64 MiB receiver correctly refused the download.

The matching baseline and candidate share the cached #473 prerequisite. The fixture, model and quota match across runs. Parallel transfers left different amounts of verified data at shutdown, and the fixture records and checks the actual saved pieces and storage arithmetic. The test uses an ordinary manual retry after clean helper restart. [Matching baseline run](https://github.com/sunnyriverr/btx/actions/runs/42942736130) · [Candidate and pristine stock control](https://github.com/sunnyriverr/btx/actions/runs/42941684877)

The three added store regression bodies passed 59 assertions in a component fixture with its own temporary directory. The full modified test source passed a syntax check. The run recompiled the changed catalog and helper files and linked them with compatible retained objects. A clean project build, full unit suite, native Windows/macOS and WAN remain unverified.

See [manifest.json](manifest.json) for source and binary identities, [baseline.json](baseline.json) and [candidate.json](candidate.json) for observations, and [maintained-cases.log](maintained-cases.log) for the regression results. The existing retrieval fixture and BTX author notices are retained.
