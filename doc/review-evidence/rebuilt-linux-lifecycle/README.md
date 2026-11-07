# Untouched rebuilt Linux package — guard/helper lifecycle PASS

Official archive SHA256 `796b9edd064272b1f443cf3e08646565936183f9f1e15339cad60e84e1014b32`, asset721231861,158893566bytes. Published source mapping2f3b574867c11ab79eba829123689b76e6137a38; producer build not independently reproduced. [Native run42413365762](https://github.com/sunnyriverr/btx/actions/runs/42413365762), exact fixture8f15d29e1960d33ff7209d8232856a9043f86a22.

This tests the actual rebuilt download without overlay, binary replacement, custom helper/guard path, manual helper or source build. It is separate from the earlier435 old586archive-plus-staged-addition result. Existing case logic is unchanged; only its expected source audit pin changes0ac→2f3. case-reuse.json records both hashes; currentcaseSHA527413739293f9ac2e4a419c8b4a49cb075febd94fa5cb0e860c4b163bd5794d.

## Executed result

59checks pass on Ubuntu24 x86_64. Node3306 directly owns helper3498 and guard3499; restartednode7188 directly owns helper7380 and guard7381. Actual/proc executable/parent/start-time records agree with live RPC/IPC readiness. Guard boot IDs differ across restart; journal valid, no policy installed, automatic spend0. Twenty fresh guard observations and20ordinary node/helper health observations pass across two boots. Nonempty public model identity records survive unchanged.

All128distributed file content hashes remain unchanged. The archive already contains the regular executable hard-link sibling. Both normal RPC stops complete, with no remaining owned processes, runtime directories or test-harness fallback signals. Temporary private identity files/cookies were removed rather than archived.

## Recipe and evidence

scripts/workflow.yml, scripts/run.py and scripts/case.py are the exact executed recipe. The workflow checks out source2f3 and installs libevent-dev,libsqlite3-0,libzmq5,libgomp1; it uses no build cache. The driver downloads the release archive, verifies its digest/size, extracts normally and invokes only the existing positive guard/helper case. No old repair baseline/symlink campaign or component suites repeated. A replaced archive intentionally causes a digest failure rather than silently testing different bytes.

native/verification.json is the checked summary; native/result.json records the controller and package manifests; native/case/result.json retains fresh RPC/process/control results. Phase console/debug logs and native/collection.json retain raw file hashes. Original artifactSHA2b54cda237d9bcc65f151a8be42c3b5aed73fa4f053ac99317e6a8e102177894 was verified, then every retained rawfile byte was reverified. dispatch-receipt.json identifies the source and fork recipe; this documentation-only branch changes no product files.

## Limits

One native Ubuntu24 x86_64 run with short offline wallet-disabled regtest windows. Zero height and peers on both planes; Modelnet stays default-on, while model listen/host/seed/follow/LAN are explicitly off and storage16MiB. No inference, transfer, protected model workload, GPU, full node/security suite, long-duration uptime, native Windows/macOS or release qualification. Guard status retains model_safety_proven=false and legacy_generatemodel_mediated=false. No independent external replication is claimed. This is not a minimal-host dependency or producer-build reproducibility qualification. Normal node shutdown uses existing supervisor termination policy; internal signals were not syscall-traced.
