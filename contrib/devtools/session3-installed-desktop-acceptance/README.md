# Installed Linux desktop acceptance — prepared, not run

This is the next bounded step of the existing Linux desktop release task. Official v0.34.16 archives omit Qt and Atlas. The retained replacement candidate passes its producer's packaging gates, but those gates deliberately did not launch the installed desktop. This fixture addresses that remaining user journey, rather than repeating the build or ModelNet/SwapNet backend tests.

**Current result: local preparation and source review only.** No syntax check, import, dependency installation, archive download/extraction, BTX build, application launch, test, CI dispatch or public post has been performed for this fixture. The user's wallet and other sessions' mutable files are excluded. A reviewed script is not a passing test.

## Inputs and reuse

- Retained candidate: sunnyriverr/btx run44063898937, artifact14319148652, expires17December2026. Outer ZIP173,356,636B SHA256d9f58d9623a3e6d13b15b9e67ba2c2b16bb9b574985bbc9dcd69c4aed3daa664. Inner btx-linux-desktop-074-candidate.tar.gz173,082,807B SHA256915fae283089a325df65ef7521fffd6e30f5faa8d0bc8f2d77a2b6af52348a57.
- Compiled source074dac167c26c1e091198f691ed5727817dba88a with the explicit reviewed Python selector overlay delivered in PR822. This is not an unmodified official archive or qualification of release-0.34.17. Atlas is the producer's explicitly reused, source-tree-equivalent source88 component, not a newly compiled Atlas.
- `inputs.json` binds sizes, source, patch, exact installer Git blob737c829b16e0fe3ac8b6f964e864537cf0e8dbc1 and producer records. `pins/` contains the existing retained JSON records; no new runtime evidence.
- Session2's retained runtime recipe and historical acceptance run43499330842 are reused with original credit. Its old source88 success is not a pass for this changed archive. JPP supplied the packaging/acceptance foundations; Numair supplied integration. The prior producer's static gates and previous execution limitations remain in the existing packaging report.

## Prepared journey and decision

1. Verify the exact artifact metadata, complete outer ZIP and inner tar digests. Compare the admitted producer records, tar member types/modes/sizes/link targets, extracted file bytes and modes. Check installer bytes before invoking it.
2. Source the exact upstream installer and call only `install_prebuilt_release_tree` into a fresh private prefix. Its normal version probes run in a future authorized attempt; updater main/download/signature/activation/source-build paths are not called. Compare all installed bin/lib/libexec content with that same archive; permit only the installer's own manifest addition.
3. Use that **same installed prefix** for a PID-owned Qt regtest window and Atlas's real native cookie picker and endpoint/chain/genesis confirmation. Require two LIVE LOCAL/regtest/zero-block observations while Atlas remains alive, then ordinary window close and node stop. Keep actual screenshots for later visual review.
4. Sequentially start that installed node twice against one fresh disposable datadir. Require ten ordinary helper/guard health observations per boot, direct child/process identity, unchanged local public identities, clean CLI shutdown and fresh restart identities. No transfer, inference, retrieval cancellation, swaps, wallet creation or payment.
5. Require unchanged installed payload and input archive, no fallback signals, no surviving owned processes and removed private runtime. Missing phase/result, timeout, skip, wrong chain, ambiguous UI, crash or dependency failure is non-PASS. Preserve failure evidence; no automatic retry or rebuild.

A future complete pass supports only this exact archive's Ubuntu24 x86_64 installed desktop/local connection/ordinary restart journey. It does not certify all desktop functions, other distributions, physical desktops, wallet spending, signed updater flow, every Python dependency or official release adoption. A failure is first classified as fixture/setup, dependency, candidate behavior or external infrastructure before a product fix is proposed.

## Isolation and finite bounds

Prepared workflow `workflow.yml` is not installed or dispatched. Its future destination is .github/workflows/session3-installed-desktop-acceptance.yml on the dedicated codex/ci-session3-installed-desktop-074 fork branch, with this directory as contrib/devtools/session3-installed-desktop-acceptance. It requires an explicit manual execute=true input, exact repository/ref checks, read-only GitHub permissions and no cancellation of a live run.

Ubuntu24.04 x86_64 only; initial free-space floor6GiB and controller floor4GiB. One job,36minute hard cap; download240seconds, dependency step9minutes, desktop/controller step16minutes. Child limits: installer90seconds, GUI300seconds and lifecycle240seconds. On interruption the GUI gets100seconds and lifecycle60seconds for cleanup; the enclosing780second timeout has120second final containment grace. Timeout never satisfies acceptance. Fresh HOME/XDG/install/datadirs live only below the runner's unique temporary root; output lives separately. Cookies and private runtime are not uploaded. Only declared result/log/screenshot directories are retained for14days; no downloaded archive is republished automatically.

Host GTK/WebKit/display libraries are declared requirements. The archive is not a sealed desktop image. No dev toolchain, Torch, Transformers, model download or alternate helper is installed by this acceptance recipe. Loader diagnostics and Atlas process mappings are evidence of the selected environment, not a universal absence-of-host-dependencies claim.

## Review and next step

See `independent-review.md`, `gui-review.md` and `lifecycle-review.md`. Source review corrected directory-mode handling under private umask077, direct hardlink metadata validation, the old recipe's unasserted second connected observation, and timeout cleanup grace/handling. These corrections are not runtime-tested.

`payload.sha256` binds the prepared executable/configuration inputs; `preparation-receipt.json` records the final source-only state. The next useful step, only when authorized, is one bounded no-build Ubuntu run after refreshing artifact availability, peer bookings, branch/workflow routing and payload identity. No upstream post is needed before evidence exists. A real pass must be reviewed with screenshots and detailed phase results before any consolidated desktop handoff; Numair's official asset/adoption decision remains separate.
