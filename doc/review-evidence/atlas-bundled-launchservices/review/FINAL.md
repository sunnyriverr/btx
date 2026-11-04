# Final artifact review — bundled Atlas Launch Services

**PASS for the bounded four-case native bundle/event result.** This is artifact/source review of coordinator-observed UI results, not a second execution or independent reproduction of the native UI. No UI, test, build, GitHub or ledger action was performed by this reviewer.

## Provenance verified

- `source-compare.json` contains one commit from accepted afd65919 to target `e70c81f03b76c5e62712ebb51dfaac7d41295af2`; the only changed file is `.github/workflows/atlas-native.yml`. The prior Atlas export can therefore represent the current Atlas code without inventing an implementation delta.
- All228 recorded exported file hashes match the retained task source. The only additional source-directory files are four Tauri-generated schema JSONs under `src-tauri/gen/schemas`; no missing recorded input or changed recorded source was found.
- The official Tauri CLI archive matches its recorded published SHA256, and the executable matches `cli-identity.json` (`tauri-cli2.12.2`).
- Build command uses genuine `tauri build --ci --bundles app --no-sign -- --offline --locked -j1`. `build.py` removes TAURI_CONFIG/signing overrides and uses pinned Rust1.95 with retained dependency/target cache. Exit0 is recorded. This is a cached build, not a fresh dependency build. Minimum recorded free disk3,414,212,608bytes exceeds1.25GiB.
- All four recorded bundle-file hashes match the retained app, including executable `8cbeae85f0b66f3c674c96c12914f562919b49decb684d5b71f811566b5a47c0`. Info.plist has original dev.btx.atlas identity and both URL schemes. The bundle is arm64 and locally ad-hoc signed; signature verification exit0 is recorded. No notarization or release qualification follows.

## Cases and oracle

Launch receipts use `open -a <actual bundle> <URL>`, not `--args`; this exercises targeted Launch Services URL delivery. Cold cases have no owned app PID beforehand and one afterward; warm cases retain their established PID. Payloads and binary hash agree across launch receipts, observation records and summary.

The four accepted cases are cold-btx, warm-repeat-btx, cold-p2p and warm-p2p. Each has a coordinator observation of its exact native visible preview, then modal absence and later quiet observations with advancing normal read-only refreshes. There were no direct native queue invocations/injections. The user completed cold connection prompts; LIVE LOCAL and exact previews were subsequently observed by the coordinator rather than inferred from confirmation.

Three exact after-close intervals verify from explicit timestamps: warm-repeat-btx30.180seconds, cold-p2p41.366seconds and warm-p2p26.543seconds.

Review caught one timing-label issue: cold-btx has no explicit close timestamp, so25.606seconds is preview-to-later-quiet, not an independently established after-close duration. The coordinator corrected the observation JSON, summary and REPORT before closeout. The report now retains advancing post-close refreshes without inventing a close time. No rerun was needed.

The earlier warm-btx launch remains an unqualified pilot: an attempted Close left the same modal visible, and the artifacts do not determine whether the click missed or another delivery existed. A distinct URI with the verified CloseDialog control supplies the accepted warm case. The report retains that ambiguity and does not claim all five launches were proven duplicate-free. This is a finite observed sequence, not a universal exactly-once guarantee.

Raw AX/screenshot files were not archived. Structured observations are coordinator transcriptions supported by native-tool history, not replayable automated UI assertions. That limitation is explicitly retained in REPORT.md.

## Cleanup checked

Recorded app/node PIDs are absent at review. Disposable scratch directory and visible cookie copy are absent. The two original Application Support files currently match their pre-test hashes exactly. The backup directory was moved back during restoration, so its old backup path need not remain populated.

Before/after handler snapshots are identical: both schemes and btx document handler return to null, document UTI unchanged. During-test snapshot shows the temporary dev.btx.atlas registration. Unregistering the retained test bundle succeeded; unregistering the original build output returned -10814/not found, and cleanup.json preserves that result. Matching final snapshots support restoration of the measured associations, not a complete proof of every Launch Services registration.

## Claims and disposition

REPORT.md accurately identifies the exact current source, default genuine bundle, cached build and local ad-hoc signing; distinguishes the four accepted cases from the pilot; corrects the timing label; discloses user assistance, finite observation and non-archived raw UI outputs; and limits the older node to read-only fixture use. Source/bundle hash claims and the stated90.2second build/minimum-disk arithmetic agree with the receipts.

This adds current integrated package/OS-event evidence beyond accepted direct-executable tests and reuses repch1c's older bundle work. Targeted app dispatch does not qualify default-handler selection or installer association, even though registration temporarily made this app the handler. No Windows/Linux, arbitrary document association, signed/notarized installer, production wallet, payment, validation/mining/model-inference or release result is supplied. Retain only sanitized node logs in any public package.

No additional runtime test is needed for this bounded result. Coordinator can record completion and prepare the short273handoff with the existing limits under the publication hold. Reviewer resources are released.
