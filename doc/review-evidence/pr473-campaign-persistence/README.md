# PR #473 campaign save and restart

**The patch preserves the previous campaign file byte for byte. Both helpers still acknowledge a failed save, and the acknowledged increment disappears after restart.** This review uses repch1c's exact PR patch.

| Observation | Release baseline | Release baseline plus #473 |
| --- | --- | --- |
| Seed and normal restart | Original campaign at 1 atom | Original campaign at 1 atom |
| Write failure | EFBIG writing campaigns.json | Short write and EFBIG writing campaigns.json.tmp |
| Wire reply and live state | error:null, pledged_atoms=10000001 | error:null, pledged_atoms=10000001 |
| Disk through clean shutdown | Unreadable JSON | Original file and SHA-256 intact |
| Restart with normal limits | Original campaign missing | Original campaign at 1 atom |
| Next successful write and restart | Recreated test campaign persists at 3 atoms | Original campaign persists at 4 atoms after adding 3 |

The recovery step used a new increment after reading the restarted state. The baseline recreation restored the ability to write. The original baseline campaign remained lost.

## Inputs and executed runs

- Release baseline [dac9aee5](https://github.com/btxchain/btx/commit/dac9aee53520bd49ed320ec7a49b9072fc7d88d9) plus [PR #473 at 15b337e2](https://github.com/btxchain/btx/pull/473/commits/15b337e2b0ab523fb59f181356f88a4283ed2cd8). Tested integration tree ed72649dc18f4eaf55c9a6d1a2b171e587b482dd.
- [Helper builds](https://github.com/sunnyriverr/btx/actions/runs/42787985840) used the verified checkpoint, GCC 11.4 and static OpenSSL 3.5.9. See the [build result and binary hashes](build/result.json).
- [Native run](https://github.com/sunnyriverr/btx/actions/runs/42789096988) used the same [runner](recipe/run_native.py) and [workflow](recipe/native-workflow.yml) for both binaries. The workflow consumes pinned fork artifacts.
- [RPC and restart records](native/result.json), [baseline file trace](native/base-campaign-io.log), [candidate file trace](native/candidate-campaign-io.log), [provenance](provenance/completion-receipt.json) and [SHA-256 manifest](manifest.json).

One disposable sequence per variant on Ubuntu 22.04 x86_64 through the real helper Unix socket. The helper had an 8,633-byte RLIMIT_FSIZE through clean shutdown and restarted with the normal limit. The trace confirms the kernel write error. Scope is the per-process limit and local pledge accounting. Physical disk exhaustion, the btxd proxy, wallet operations, peers, spending and other platforms were outside this run. Both helpers exited cleanly and their disposable directories were removed.
