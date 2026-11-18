# Exact installed desktop acceptance — PASS

18 November2026 Brisbane. [Ubuntu run44198893852](https://github.com/sunnyriverr/btx/actions/runs/44198893852), control6d719e9191cea74a2e5ba7081e6beb02d7fd38bd, completed successfully in230seconds. The actual install/GUI/lifecycle controller step took72seconds. **All five required controller phases pass**, with detailed GUI and lifecycle results, not just a green workflow badge. No BTX rebuild, upstream post or real-wallet access occurred.

## Exact subject and reused evidence

Candidate artifact14319148652 from producer44063898937/control3145c20fe7f3c215a06398a052f573d5d5bf47aa. Complete outer ZIP173,356,636B SHA256d9f58d9623a3e6d13b15b9e67ba2c2b16bb9b574985bbc9dcd69c4aed3daa664; inner btx-linux-desktop-074-candidate.tar.gz173,082,807B SHA256915fae283089a325df65ef7521fffd6e30f5faa8d0bc8f2d77a2b6af52348a57.

Compiled product source074dac167c26c1e091198f691ed5727817dba88a plus the explicit reviewed Python-selector packaging overlay from PR822. The bundled Atlas executable is the producer's reused source88/tree-equivalent component, not a fresh Atlas build. This is not an unmodified official archive or qualification of the whole release-0.34.17 branch. Earlier package/ABI gates remain separate producer evidence; its historical final metadata-GET failure is not rewritten as a successful producer workflow.

Credit JPP for the packaging/acceptance foundations, Numair for integration, and Session2 for the retained source88 desktop recipe. Session3 adapted that recipe to one installed prefix. Old source88 runtime success was design evidence only; this run independently executes the changed retained candidate. Earlier runs44191690985,44193516952 and44195321636 preserve their setup/fixture failures and narrower partial results.

## Actual acceptance results

| Boundary | Verified result |
| --- | --- |
| Inputs and archive | Exact source/configuration hashes, producer metadata, complete outer/inner digests, packaging patch records, archive root and902 child paths, type/mode/size/link metadata and extracted file hashes passed. |
| Host prerequisites | Signed Ubuntu sources and declared desktop dependencies installed. The kernel mirror index attempt did not complete; the bounded selection continued and chose Princeton. This observes index-stage failover, not a package-pool failure/recovery or universal mirror-resilience result. FileChooser portal reports version3. |
| Real prebuilt-tree installation | Exact source074 installer function stages the admitted bin/lib/libexec trees, runs real btxd/btx-cli version probes and writes its prebuilt manifest. Installed bytes/modes/links match the admitted tree, with only that manifest addition. All subsequent apps and node boots use this same private installed prefix. No updater main/download/signature/activation/source-build path is called. |
| Installed daemon control | Actual installed libexec/btxd.real answers local CLI RPC with regtest, height0, zero peers. GUI nodes use wallet-disabled/network-disabled datadirs and modelnet=0. |
| Qt | Actual installed libexec/btx-qt.real and its original process start identity own the regtest window. Screenshot qt-main.png shows clientv0.34.16, regtest, height0 and disabled network activity. The window closes with exit0. |
| Atlas/native local connection | Actual installed Atlas welcome window, native cookie picker and native confirmation were exercised through accessibility/window controls, without bridge injection. Confirmation matches127.0.0.1:46161, regtest and the RPC-observed genesis521ad0951ed299e9c56aeb7db8188972772067560351b8e55adf71dbed532360. Two observations5.08seconds apart show a live app, LIVE LOCAL, regtest and0blocks. Atlas and its disposable node close normally with exit0. |
| Ordinary helper/guard lifecycle | Two installed daemon boots with one normal restart over a fresh wallet-disabled offline regtest datadir. Each boot has10 healthy helper/guard observations;43 recorded checks all pass. Daemon/helper paths and direct-child ownership, persisted local public identities, stable process identity per boot, fresh restart process identities and fresh guard boot are checked. Both boots stop with exit0 and no installed process remains. No model transfer, retrieval cancellation or inference is exercised. |
| Final integrity/cleanup | Parent, GUI and lifecycle results all PASS. No fallback signals, cleanup errors or surviving owned processes; private runtimes removed. Installed payload and archive identity remain unchanged. No manual helper launch. All phase outcomes and required JSON results satisfy the final completeness gate. |

Lifecycle boot1: node5275, helper5468, guard5469. Boot2: node9151, helper9344, guard9345. These are disposable runner identities, not production service IDs. The two public-identity lists and before/after package hash maps are equal; each guard boot differs as required.

## Screenshots and claim limits

The five stored PNG hashes match their recorded capture hashes. Parent visual review checked Qt main, Atlas welcome, native picker, native endpoint/chain/genesis confirmation and connected status. The connected screenshot visibly shows LIVE LOCAL, regtest,0blocks and0money peers. The Qt window extends beyond the1440x1000 virtual screen; it is valid launch evidence but does not qualify layout, responsiveness or usability at that size. No cookie contents, personal wallet or private key is displayed.

The scope is Ubuntu24.04 x86_64 virtual X11 with declared host GTK/WebKit/display libraries. No cross-distro/physical-desktop/GPU/CUDA/Windows/Mac qualification, full UI workflow sweep, wallet creation/payment/recovery, mainnet sync, SwapNet operation, ModelNet transfer/inference, signed-updater trust flow, current rebuilt Atlas or official release adoption is established. Images and raw records prove this scoped journey, not general release readiness.

## Retention and resource closeout

Result artifact14381370302:708,633B ZIP, SHA25634645ac7a81a92a0c9ae1c595f66e948f1a7f89ed37d46f36377f479cc57bbff. Whole ZIP hash and CRC independently verified after local download. It contains29 records, including all three result JSON files, two boot logs, ownership/loader/host records and five screenshots. It expires1December2026 at23:26:54UTC unless retained elsewhere. The exact fork fixture is immutable at control6d719e91; future public handoff needs a permanent verified evidence capsule rather than relying solely on expiring artifacts.

The hosted job is terminal. Normal shutdown and runtime removal are recorded; no owned processes, local UI, VM or build resources remain in use. Release the short ref/runtime/workflow-routing execution claim; retain task/root ownership for a possible authorized handoff. No peer messages, peer mutable cache/UI/VM changes, real wallet/keys/coins, production changes or upstream publication occurred.

The local acceptance finish line is now satisfied. Next useful step is one concise consolidated desktop handoff after final scope/head/overlap review and permanent evidence preparation, only if authorized. Numair's official asset/version/upload/adoption decision remains separate. Do not repeat these passing checks or broaden the campaign merely to keep the lane occupied.
