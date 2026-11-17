# Retrieve cancellation save errors and retry — Linux qualification

**Same maintained regression and real-helper driver fail on baseline and pass with the fix.** The repair reports failed saves and lets an operator retry persistence before restarting; it cannot guarantee cancellation persists while storage remains broken.

## Exact inputs and entry point

- Product baseline: `release-0.34.17` at `cd3078e76398b20b7f500acd1348a5b5455f3d5e`, plus the new maintained regression in both builds.
- Candidate: the same tree/test with only the helper change in [candidate.patch](candidate.patch).
- Executed public fork [run 44069193026](https://github.com/sunnyriverr/btx/actions/runs/44069193026), CI commit `2495347de98fc60d929a3ae861603b8553835ecb`.
- Ubuntu 22.04 x86-64 container on a hosted Linux runner; GCC11.4 and pinned OpenSSL3.5.9. Exact container, toolchain setup and build commands are in [recipe/workflow.yml](recipe/workflow.yml), [recipe/setup.sh](recipe/setup.sh) and [recipe/qualify.py](recipe/qualify.py).
- The retained checkpoint was hash/mode/timestamp verified, then current tracked source was overlaid without rewriting identical files. Baseline33 and candidate13 planned build actions preceded compilation. This was an incremental current-source build, not a clean release rebuild.

## Results

| Check | Baseline | Candidate |
|---|---|---|
|All36 selected `modelnet_first_run_tests` cases|Only new cancellation-save regression fails;35existing cases pass|36pass|
|Directory at disposable `retrieve_jobs.json.tmp` during cancellation|Returns cancelled:true/error:null; repeat has no save error|Both requests return IO_ERROR with retry instruction|
|Actual worker stop after partial transfer|Stops with failed/stopped; verified pieces retained|Same|
|Storage repaired, same cancellation retried before shutdown|Returns cancelled:false but old active snapshot remains|Returns cancelled:false and removes target from saved active snapshot|
|Healthy cancellation and12second quiet restart|Pass|Pass|
|Ordinary interrupted download restart|Same job, saved pieces kept, exact16,777,291-byte completion|Same|
|Cleanup|9helper starts stopped cleanly; runtime removed|Same|

The native driver records exactly three expected contract failures on baseline and none on candidate; it rejects unexpected control failures. [records/qualification.json](records/qualification.json) records source/binary hashes, commands, exit statuses and timing. [RESULT.json](RESULT.json) gives the consolidated receipt and limits. [evidence-manifest.json](evidence-manifest.json) hashes every raw record. Both full XML logs retain the15,616filtered cases outside the selected suite; those tests were not run.

The normal-restart output SHA384 in both phases is `fd6b50534a695af7d8515366de9deb5573443d347945451055788c4a3ed6db8216eee7432e6830c064fdd6324394c123`. Source and every committed piece were checked, not only JSON job status. The matched native checks run through actual helper processes, PQ1 and UnixRPC; no persistence or worker test hook is used.

## Reproduction

The linked run executed `proposal/qualify.py`, using the exact copies under [recipe](recipe). It builds the two targets on the pinned baseline with the new regression, runs `test_btx --run_test=modelnet_first_run_tests --log_level=test_suite --logger=JUNIT,all,<output>`, and invokes `native.py` with the produced helper SHA256. It then applies only the helper patch and repeats the identical suite/driver. See the recorded commands and logs rather than treating this paragraph as a separately executed clean-build recipe.

`recipe/native.py` starts fresh local providers, waits for a verified4MiB piece, injects a directory at the temporary job-list pathname, cancels, waits for actual worker termination, checks repeated failure and healthy retry before shutdown, then verifies quiet reopen. Separate healthy-cancel and uncancelled-restart cases preserve legitimate behaviour. Result validators and their nine offline controls are supplied; missing/skipped selected tests and unrelated failures are rejected.

The staging script requires access to retained checkpoint14307015983 and its original runner workspace layout; it expires1December2026. The workflow and hashes document the executed cache path. A new environment can build the pinned source normally instead, but that reconstruction was not separately executed here. Qualified binaries are retained as artifact14323625595 until1December11:12:46Z. The full868,181-byte records ZIP was downloaded and verified against digest `6f079a8b4842c763e18ff8c3a68511552adab3252651fa758477cc53d278b638`; binary hashes are producer-verified and their larger artifact was not downloaded onto the Mac.

## Limits and credit

Not tested: full node or full test_btx suite, native Windows/macOS, public WAN, physical disk exhaustion, permission combinations, abrupt crash/power-loss durability, inference or release qualification. Actual terminal-history pruning was not forced. The maintained dispatcher test covers terminal/absent IDs and preserves another active job; actual live worker-to-failed retry is covered natively. No wallets, real funds or production data were involved.

The patch preserves repch1c's truthful cancellation-outcome contract from [#661](https://github.com/btxchain/btx/pull/661) and worker-lifetime fix from [#766](https://github.com/btxchain/btx/pull/766), and reuses the existing maintained first-run and retrieval fixture shapes. Original authorship remains in the base history. AI tools assisted implementation and qualification; the claims above are bounded by the recorded execution.
