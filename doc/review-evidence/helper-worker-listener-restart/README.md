# Linux helper restart: worker descriptor cleanup

Fix `ef10c7bea81a7045a471113809edf23fb4a29c0e` on `codex/fix-helper-worker-listener-restart`, based on accepted `ecd9310a8b35dbf1260d1a64e0ff39bb50e7a629`.

A configured resident model loader can survive helper failure and keep the helper's model TCP listening socket open. A replacement helper still answers its Unix-socket RPC but cannot bind that TCP port. Closing helper-owned descriptors in all four worker children after standard-I/O setup restores the listener without terminating the resident worker. Standard descriptors 0/1/2, worker arguments and parent bookkeeping are retained.

repch1c reported this as [#338 item18](https://github.com/btxchain/btx/issues/338). Sunny River authored the earlier guarded correction and this integration; JPP supplied process-boundary and handoff guidance. Accepted #354 closes node-to-helper descriptors before the helper creates its own listeners; this fixes the subsequent helper-to-worker boundary. The code commit retains credit. No validation, consensus or signer policy is changed.

## Actual result

One final execution per case/configuration on ecd9310a. The exact same finite configured-adapter fixtures were used for both actual helper binaries.

| Observation | Baseline | Fix |
| --- | --- | --- |
| Resident worker stays alive after owned helper failure | yes | yes |
| Worker retains the old helper TCP listener | yes | no |
| Replacement local RPC responds | yes | yes |
| Replacement owns the TCP listener | no | yes |
| Idle restart and explicit-unload listener recovery | pass | pass |
| Inference stdout, generation stdin/JSON, llama argv/stdout | pass | pass |
| Intentional adapter error and later helper responsiveness | pass | pass |
| Local RPC while each control worker runs | pass | pass |

Baseline resident raw logs show the bind/listen failure. Releasing that worker does not make the already-running replacement rebind during the bounded observations; one further clean helper restart recovers. The candidate recovers at the first replacement while its resident worker remains live.

The baseline restart script returns 1 by design. Its legacy unload row also has `regression_pass=false` because that field includes inheritance observed before unload; the actual post-unload listener recovery is healthy and is separately checked. Both controls scripts return 0. Read baseline-cases.json and candidate-cases.json for the observations rather than treating any arbitrary assertion failure as the intended result.

## Build and identity

Native Alpine3.22.4/aarch64/musl, Linux6.12.81, GCC14.2, OpenSSL development3.5.9. Actual root-CMake Release/O1 `btx-modeld` target built and linked. Both sides use `CMAKE_CXX_FLAGS=-include cstdint` for the existing membership-header prerequisite; the original failing object diagnostic is included. No prerequisite product-source edit. This does not establish that the unmodified default profile builds on this toolchain.

Current baseline/candidate use the retained complete project build with all newly accepted deltas rebuilt: baseline21.01s, correction14.01s. Both verbose logs prove helper.cpp compilation and executable linkage; the actual helper compiler command matches. This is an affected-target incremental qualification, not a fresh full build on ecd9310a. The earlier46 cold build and historical three-run results are not counted as current repetitions.

Executed baseline ELF SHA256: `4c6b59419727bc5ad050ab0b46ff7abf374212a1af26f0f3525e99cbcc2070ad`.

Executed candidate ELF SHA256: `b491be34e9438fcf9ada43d6d6f04a44353f975beb526009064ad06a63c29e53`.

The runtime test used commit0c9b339e. The final code commit differs only in commit-message wording: both have tested tree `d4c9fcc4824739ab99e31fa047bf9e888e14e310` and the same accepted parent. See metadata-amendment.json. All14,165 tracked regular source-file hashes matched the staged accepted tree, with only candidate helper.cpp changed. Generated files and symlinks are outside that regular-source manifest.

## Reproduce on disposable Linux

Use ordinary project dependencies, Python3, a C compiler and `/usr/bin/lsof`. The published `.py` and `.c` fixtures are byte-identical to those executed; compile their finite adapters locally. No prebuilt executable is needed from this evidence branch. Use separate baseline/candidate worktrees and separate mutable build directories:

```sh
git worktree add --detach /tmp/btx18-before ecd9310a8b35dbf1260d1a64e0ff39bb50e7a629
git worktree add --detach /tmp/btx18-after ef10c7bea81a7045a471113809edf23fb4a29c0e
for side in before after; do
  cmake -S /tmp/btx18-$side -B /tmp/btx18-build-$side -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS_RELEASE=-O1 \
    '-DCMAKE_CXX_FLAGS=-include cstdint' -DBUILD_TESTS=OFF -DWITH_MODELNET=ON \
    -DBUILD_DAEMON=OFF -DBUILD_CLI=OFF -DBUILD_GUI=OFF -DBUILD_TX=OFF \
    -DBUILD_UTIL=OFF -DBUILD_WALLET_TOOL=OFF -DENABLE_WALLET=OFF \
    -DWITH_SQLITE=OFF -DWITH_ZMQ=OFF -DWITH_USDT=OFF -DWITH_CCACHE=OFF
  cmake --build /tmp/btx18-build-$side --target btx-modeld -- -j1
done
# In this evidence directory:
cc -std=c11 -D_DEFAULT_SOURCE -O1 runtime/helper-worker-inheritance/adapter.c -o runtime/helper-worker-inheritance/adapter
cc -std=c11 -D_DEFAULT_SOURCE -O1 runtime/helper-worker-fix/control.c -o runtime/helper-worker-fix/control
python3 runtime/helper-worker-fix/reproduce.py --binary /tmp/btx18-build-before/bin/btx-modeld --out /tmp/btx18-before-restart
# Expected baseline exit1; resident worker live, replacement_rpc_responds=true,
# replacement_has_tcp_listener=false. Idle/unload replacement listeners must be true.
python3 runtime/helper-worker-fix/reproduce.py --binary /tmp/btx18-build-after/bin/btx-modeld --out /tmp/btx18-after-restart
# Expected candidate exit0; all three replacement listeners true, no inherited listener.
python3 runtime/helper-worker-fix/controls.py --binary /tmp/btx18-build-before/bin/btx-modeld --out /tmp/btx18-before-controls
python3 runtime/helper-worker-fix/controls.py --binary /tmp/btx18-build-after/bin/btx-modeld --out /tmp/btx18-after-controls
# Both controls commands must exit0 with all four cases passing.
```

The two fixture entry points above were executed against both recorded binaries. Fresh two-worktree clean builds in this documentation are a portable recipe, not a claim that those additional cold builds were run. Output directories must be absent. The fixtures create only disposable model data and loopback listeners, explicitly stop their own helper processes, and use finite owner-configured adapters. They are an external regression, not registered in the default test runner.

## Limits and retained records

No actual GPU/model computation, authenticated PQ1 transfer, full node, unit/functional suite, fresh macOS/Windows, glibc/other Linux architecture, stress or release qualification. Windows fork behavior and guards are preserved by source review only. Listener recovery does not prove a complete authenticated model session.

The full local archive, including both executed ELF files, hashes to `b0b29bde2374579ad972e548be91a44c78327c309e4081bdfa1cdc84a7db114d`; it is retained locally rather than uploaded. The public branch supplies readable source, results and logs. public-copy-provenance.json maps original/public hashes; only unnecessary local identity/path text was redacted. Private qualification-era status flags in captured summary.json are historical, not this branch's publication status. The full original archive manifest is retained as an identity catalog; its binary files are not part of this branch. Internal artifact review is not an independent platform rerun.

VM stopped, memory restored1GiB and original2GiB disk cap unchanged. Owned fixture processes exited and ports/disposable directories were released. No production node, wallet or peer-session work was used.
