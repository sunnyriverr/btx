# Atlas bundled Launch Services acceptance — PR273 evidence

**PASS, scoped: both btx: and btx-p2p: reached their exact native preview in the checked cold/warm sequences on a genuine current Atlas app bundle. No duplicate was observed during subsequent normal UI refreshes.** This is acceptance evidence for the existing Atlas change.

## Target and build

Exact target: `btx-035/atlas-native@e70c81f03b76c5e62712ebb51dfaac7d41295af2`. All228Atlas export files match their prior immutableafd65919manifest; GitHub comparison proves gui/atlas unchanged at e70. Hashes were reverified after build. This uses current application source, not the prior executable/test-identifier wrapper.

Official Tauri CLI2.12.2 aarch64 archive SHA256: `4a27a61b06e688308a5c17333008b6df52fd5780fa7a313a9ce8fb4a80dfb9ac`, checked against its published digest. Rust1.95.0 offline/locked release, one job. Genuine `build --bundles app` completed in90.2s using the completed-task dependency cache. No TAURI_CONFIG/identifier override: default dev.btx.atlas, generated Info.plist declares btx/btx-p2p. Bundler signing was disabled; the owned copied bundle was locally ad-hoc signed and strictly verified. No signing credentials/notarization. Binary SHA256: `8cbeae85f0b66f3c674c96c12914f562919b49decb684d5b71f811566b5a47c0`. Native macOS26.5.1(25F80), arm64.

Build/source/CLI/app receipts preserve exact identities. Minimum measured free space3.414GB exceeded the1.25GiB reserve. Reused target now reflects default-identity/custom-protocol genuine bundling; its executable must not be reused as the older overridden-identity build. Previously copied app binaries are preserved; see cache-state.json.

Parser/direct-argv/model/dialog/ACL checks were reused. repch1c's older real-bundle tests and278fix are prior evidence; currentafd65919reports and Numair's summary explicitly excluded this bundle retest. No newer matching public result was found; private work remains unknown.

## Native results

Each dispatch used `open -a ABSOLUTE_BUNDLE_PATH URL`, without --args. This tests targeted Launch Services delivery. First instance absent before each cold launch; warm launch retained the same PID. Normal frontend/native connection used a disposable wallet-disabled, modelnet-disabled, peerless regtest node. That older hash-identified node supplied only read-only UI connection/polling infrastructure. The user completed two native confirmations after computer control timed out; LIVE LOCAL and exact previews were independently observed afterward.

| Case | Exact preview | Process | Later observation |
| --- | --- | --- | --- |
| Cold btx | btx:atlas-ls-cold-btx?amount=0.125 | new78709 | samples4→6, no recurrence |
| Warm btx, decisive control | btx:atlas-ls-warm-repeat-btx?amount=0.125 | same78709 |30.180s after close, samples16→19 |
| Cold btx-p2p | btx-p2p://atlas-ls-cold-p2p.invalid:8333 | new79261 |41.366s after close, samples3→7 |
| Warm btx-p2p | btx-p2p://atlas-ls-warm-p2p.invalid:8333 | same79261 |26.543s after close, samples11→14 |

Cold-btx's25.606s interval begins at its preview observation before the Close action; it is not an independently timed after-close duration. The two post-close observations do show advancing normal refreshes without another preview. All windows are finite sampled observations, not continuous tracing or a universal exactly-once proof.

The coordinator inspected native CUA accessibility/visible preview state and closed accepted previews normally without parsing/executing. `*-observation.json` transcribes observations/UTC times; `*-launch.json` records exact arguments/exits/PIDs/binary hashes. Screenshot/AX outputs remain in tool history; raw files were not archived. This is structured manual observation, not an unattended UI assertion harness. No direct pending-queue invoke/injection was used: that command drains the queue and competes with frontend polling.

An extra initial warm-btx pilot showed the right preview, but the first bottom-Close action did not visibly dismiss it. This did not prove duplicated delivery and was not counted as the decisive result. A distinct URI and the verified top CloseDialog control provided the unambiguous warm acceptance above. Pilot and repeat are retained; no product bug is claimed from the ambiguous interaction.

## Cleanup and limits

cleanup.json verifies owned app/node stopped, zero peers/regtest0 before shutdown, and temporary cookie/datadir removed. Original Atlas application data was moved aside and restored with identical2file hashes. Initially all queried scheme/document handlers were absent; macOS temporarily assigned the test bundle. Unregistering only the two newly generated owned paths restored the exact prior handler snapshot. Test-created app/WebKit/cache state is retained under test-state outside restored live paths. Production/PQWallet were untouched.

This checks targeted native Launch Services delivery into a locally ad-hoc bundle. It does not qualify default-app selection, Finder document association, signed/notarized installation, Windows/Linux, payment/model execution, Qt parity, mainnet/node validation or a release. No cookie value entered the page/evidence. Native connection assistance is disclosed rather than counted as automation success.

