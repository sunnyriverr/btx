# Atlas afd65919 — native Mac sole-link check

PASS for the one requested direct-executable second-instance case on macOS26.5.1 arm64. Exact upstream target: `afd6591970e7f8d65871412b9d7cf03b48f30b97`. Read REPORT.md for observation and limits; summary.json, launch receipt and UI observations are the result. No product patch is included.

## Reproduction outline

1. Check out that exact commit in an isolated directory. On our M4 we used Rust1.95.0, the existing Cargo dependency source cache, a new target directory and the committed Cargo.lock. In gui/atlas:

   ```sh
   CARGO_INCREMENTAL=0 CARGO_TARGET_DIR=/path/to/isolated-target \
   TAURI_CONFIG='{"identifier":"dev.btx.atlas.downloadstest"}' \
   cargo +1.95.0 build --offline --locked --release -p btx-atlas -j 1
   ```

2. Bundle the resulting btx-atlas executable as a local test app using its normal bundle resources; ours was locally ad-hoc signed. This is not a signed-distribution test. The test identifier above is the only explicit configuration override; source files/Cargo.lock are unchanged. All228 exported source-file hashes are in source-identity.json; exact build command/timing in build-result.json.
3. Start the first instance, connect through its native UI to an owned wallet-disabled regtest RPC fixture and observe LIVE LOCAL with advancing refreshes. Our older fixture binary hash is recorded in REPORT.md; it supplies polling only. The native cookie picker accepted a visible private mode0600 copy of its cookie. Do not use production wallets/credentials.
4. From a terminal invoke the **same executable** with exactly this sole argument:

   ```sh
   '/path/to/Atlas Acceptance Test.app/Contents/MacOS/btx-atlas' 'btx:atlas-guard-sole?amount=0.125'
   ```

5. Observe the exact URI in the first app's native Preview BTX resource dialog. Confirm the second process exits and the first remains alive. Close the preview without parsing it; continue normal refreshes. Our two later UI observations span39.275seconds and show no recurrence; this is sampled bounded observation, not universal exactly-once proof.
6. Quit the test app, stop the fixture node and remove disposable data/cookies. No transfer, payment or inference is required.

Our setup/connection needed manual UI work. The launch receipt is machine-recorded; UI observations are transcribed from tool output. This outline is not an unattended acceptance harness. It does not repeat Windows/Linux, LaunchServices, cold-start, mixed arguments, payment or full-release qualification. Numair adopted repch1c's #286 guard; this is its requested Mac integrated-head check.
