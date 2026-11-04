# Reproduce the bounded native check

This procedure assembles the commands used in the recorded test with reviewer-selected local paths. It was not separately rerun from this documentation branch. The supplied launch.py is the historical executed helper, not a portable automatic UI test; it reads local app-identity.json and records process/exit data, while the actual preview must be observed separately.

1. Use a nonproduction macOS GUI session, Rust1.95.0 and an audited dependency cache for the committed gui/atlas/Cargo.lock. Snapshot any existing dev.btx.atlas application/WebKit/cache state and current btx/btx-p2p/document handler associations. Ensure no other Atlas instance is running. Preserve wallets and existing registrations.
2. Check out exact e70c81f03b76c5e62712ebb51dfaac7d41295af2. From gui/atlas, use the official TauriCLI2.12.2 aarch64 release archive (URL/digests in cli-identity.json). Verify the published archive checksum before execution. Use a separate target/cache when another session is building. Remove test TAURI_CONFIG overrides and signing credentials from this build's environment.

```sh
cargo-tauri build --ci --bundles app --no-sign -- --offline --locked -j 1
```

3. Use the generated BTX Atlas.app, not a hand-made wrapper. Copy it to an owned test location, then locally ad-hoc sign that copy and verify its signature. Record executable SHA256 and Info.plist; original dev.btx.atlas, btx and btx-p2p declarations must be present. This does not create a notarized/release installer.

```sh
codesign --force --deep --sign - /absolute/test/BTX\ Atlas.app
codesign --verify --deep --strict /absolute/test/BTX\ Atlas.app
```

4. Start a disposable wallet-disabled peerless regtest node bound only to127.0.0.1, with a private temporary datadir and fresh cookie. This run reused an older retained node only as read-only UI infrastructure (SHA25603a3fb602e0a0dea77583f774ecf516f5875137829c2a9f6c03637f925300fc6). Do not treat it as current node/consensus qualification. No mining, payments or model execution is required. Typical fixture options: -regtest -server=1 -rpcbind=127.0.0.1 -rpcallowip=127.0.0.1 -rpcport=YOUR_FREE_PORT -listen=0 -connect=0 -dnsseed=0 -discover=0 -natpmp=0 -disablewallet=1 -modelnet=0 -dbcache=32.
5. With no Atlas process, deliver a unique harmless URI through Launch Services. Do not use --args, which would repeat the old argv path.

```sh
open -a /absolute/test/BTX\ Atlas.app 'btx:atlas-ls-cold-btx?amount=0.125'
```

6. Connect normally through Atlas's cookie picker and native confirmation to only that disposable endpoint. The cold link can queue while offline: no visible preview before connection is not evidence of loss. Verify LIVE LOCAL and the exact native preview, close it without Parse/Execute, then observe no recurrence over further normal refreshes. Record actual times/sample counters. Do not invoke atlas_pending_links manually; it drains the queue and races the frontend.
7. Send a distinct warm URI with the same open command. Verify one existing process remains, exact preview appears once, and normal refreshes after a visibly effective Close show no recurrence. If a Close action has no visible effect, classify the interaction before alleging duplicate delivery; use a distinct URI/verified action if needed.
8. Quit Atlas normally. Repeat cold/warm with btx-p2p://atlas-ls-cold-p2p.invalid:8333 and a distinct warm URI. These are preview inputs only; do not parse or join peers. The recorded result has one accepted sequence per scheme and bounded sampled quiet windows, not a universal exactly-once proof.
9. Quit owned Atlas, stop the owned node, remove its disposable cookie/datadir, unregister only the newly created owned test bundle path, and restore original app state and handler snapshot. Our cleanup also tried the generated build-output path; it was not registered, and final measured associations matched their original null values. Preserve unrelated applications.

Targeted open-a delivery does not test default-app choice, Finder file association, signed/notarized installers, Windows/Linux, full Qt parity or release readiness.
