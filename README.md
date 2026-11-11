# Search policy persistence follow-up

Repch1c authored [#553](https://github.com/btxchain/btx/pull/553) and the atomic writer in release commit `895b4bc0`.
The Mac tests used #553 `cac122a5` composed onto release `c6f9678d`. The follow-up targets the older #553 branch and carries only the atomic writer hunk as its first commit. When applying to the tested release composition, use the repair commit alone because the writer is already there. The final source files were checked against the recorded hashes of that tested composition.

Build the real `btx-modeld` target for the baseline and candidate with ModelNet and static OpenSSL 3.6.3. The recorded Apple silicon builds used AppleClang, Release with `-O0 -g0`, and GUI, wallet, Metal and ZeroMQ disabled. Run `python3 mute-save.py /path/to/btx-modeld` for each binary. The evidence copy adjusts the harness import path to load the adjacent helper fixture. The harness creates its own temporary stores and uses only Unix RPC. The stock run exits 1, losing an earlier mute after restart and reporting success during a blocked save. The candidate exits 0 with the earlier mute preserved and `IO_ERROR` on the blocked save. Both runs check a healthy retry.

[Live before](before-live.log) · [Live after](after-live.log) · [Maintained before](before-unit.log) · [Maintained after](after-unit.log) · [Binary and test hashes](matched-receipt.json) · [Source verification](source-verification.json)

The same maintained regression was linked in a temporary Boost runner against the real helper archives. The new case failed eight assertions before, and all 67 assertions across three cases passed after. It checks an existing index record, hide and unmute errors, rollback and retry. Full `test_btx`, daemon RPC forwarding, Linux and Windows were outside scope. The fixture path in the logs was shortened.
