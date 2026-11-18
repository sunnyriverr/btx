# Installed archive qualified; GUI readiness fixture failed

18 November2026 Brisbane. [Run44195321636](https://github.com/sunnyriverr/btx/actions/runs/44195321636), controlc690d8e2b8aa409299ea3365f5da0122025ebc87, one authorized Ubuntu24.04 x86_64 attempt with the unchanged retained archive and no rebuild. **Workflow result: failure.** This is partial integration evidence, not desktop acceptance or an official release verdict.

## What actually passed

- Same artifact14319148652 and complete outer ZIP digestd9f58d9623a3e6d13b15b9e67ba2c2b16bb9b574985bbc9dcd69c4aed3daa664. Controller phase artifact=PASS includes the inner tar digest915fae283089a325df65ef7521fffd6e30f5faa8d0bc8f2d77a2b6af52348a57, pinned producer/patch/source records, tar root/child/type/link metadata and extracted member byte/mode inventory. This closes the previously failed archive-admission gate for this artifact.
- Declared host dependency download/offline installation and FileChooser portal version3 probe succeeded.
- Exact source074 prebuilt-tree installer completed its real btxd/btx-cli version probes. Controller installed_tree=PASS confirms the resulting bin/lib/libexec file/link/mode inventory equals the admitted archive, apart from the expected installer manifest. The root-normalization and adapter umask corrections are now exercised together against the real archive on Ubuntu/Python3.12.
- The installed libexec/btxd.real ran from the temporary installed prefix. Actual CLI RPC returned regtest, height0 and zero peers. Atlas/Qt loader diagnostics found their declared dependencies, with Atlas GLib and DBus resolving to host libraries as intended.
- The installed payload remained unchanged. The daemon log ends with Shutdown: done; no owned process remained and private runtime was removed.

These checks do not establish that every installed component runs. Atlas remains the producer's explicitly reused source88/tree-equivalent component; the compiled node/Qt/helper source is074 with the reviewed packaging-selector overlay. This is neither an unmodified official package nor release-0.34.17 qualification.

## Why GUI and overall acceptance failed

gui/result.json records AssertionError(('qt', 'unexpected executable')). The fixture checked the newly launched Qt PID immediately. It was still executing the packaged shell launcher, not yet the libexec app; owned session observations show /usr/bin/dash and a short-lived grep child. windows() asserted prefix executable ownership before its bounded window wait could wait for that transition.

No Qt window was verified or captured. Atlas was not launched, native local connection was not tested and the two-boot helper/guard phase was not reached. An empty qt.log does not establish that Qt could or could not eventually start. This evidence identifies a premature harness check, not a demonstrated Qt defect or a successful Qt launch.

After this intermediate failure, the GUI driver terminated four remaining shell/grep processes with SIGTERM. That containment correctly makes the GUI phase non-PASS; it is not normal GUI shutdown. GUI and parent records both show no survivors, removed private runtime and unchanged package; the parent itself required no additional signals. Its phases are artifact=PASS and installed_tree=PASS, overallFAIL. The completeness collector failed as required.

## Local readiness correction and exact limits

gui-repair/gui.py makes a pending shell return no ready window and lets the existing45second Qt wait observe the actual app. It requires the exact expected libexec/btx-qt.real or btx-atlas.real, original PID start identity and a window attributed to that child PID. A different executable/identity/window cannot become an accepted observation; no timeout or acceptance requirement is relaxed.

Five local synthetic checks pass on macOS ARM64/Python3.11.14: shell-to-real-app transition with the same PID/start identity; different installed executable refused; different start identity refused; different window PID refused; and no window remains pending. All process/window observations are supplied test data. Neither a GUI, window tool nor BTX was executed in those local checks. The correction is local, source-reviewed and has not been exercised on Ubuntu. The hosted run did not contain this readiness change.

Source review missed the launcher's intermediate executable in the original fixture. The focused observation tests now model that transition explicitly. Earlier root/mode synthetic checks and this Ubuntu installed-tree pass remain valid and need no repeat merely to change window readiness. A further real run must still establish actual Qt/Atlas operation and lifecycle/normal cleanup; synthetic tests cannot supply it.

## Evidence, resources and next step

Artifact14379350840,39,336B, SHA256474e1c934dcfe0903e5a9489b25e69fb9cb367f16e48e58e6f66dd1a8e5d12ee, was downloaded and verified by whole-ZIP hash and CRC. It contains15 records, including parent/GUI JSON, installed-node log, loader logs, ownership records and host/portal logs. There are no screenshots or lifecycle results. Full terminal job log, control diff and exact remote-byte verification are retained separately.

The hosted job is terminal, the temporary runtime is removed and no process survives. Preserve all three attempts and their distinct results. Session1SwapNet and Session2ModelNet work, real wallets/keys/coins, production and upstream discussions remain untouched. No rebuild or upstream post occurred.

Next: after authorization, one bounded no-build attempt with the locally checked window-readiness correction and the same archive/requirements, refreshing ref/artifact/bookings/payload first. No automatic fourth dispatch and no desktop handoff while Qt, Atlas, lifecycle and normal GUI shutdown remain unqualified.
