# Independent source and acceptance-design review

Verdict: source identity and planned acceptance scope are sound. This is a read-only review, not an independently executed UI test.

- Compared all 228 files listed in source-identity.json with both the exported files and `git show afd6591970e7f8d65871412b9d7cf03b48f30b97:<path>`. Every byte/hash matched. The target is the integrated maintainer commit, not the earlier acbf7efb plus one-file candidate.
- build.py uses Rust1.95, offline locked Release, one job and a new task-local target. Its explicit Tauri config override changes only the test bundle identifier to dev.btx.atlas.downloadstest. Source files and Cargo.lock remain exact. It reuses the existing Cargo dependency source cache. The recipe inherits other environment variables; preserve actual build/binary provenance rather than claiming a hermetic environment.
- Numair's request6602199759 explicitly asks for this sole-btx second-instance Mac run on afd65919. The older native Mac before/after report establishes the prior failure and control behavior, so repeating that entire baseline campaign is unnecessary for this acceptance request.
- `plugin_forwards` is false on macOS; the real single-instance callback should therefore send the second process's sole URI through Host::receive_link. The normal UI drains pending links only during refresh while connected. Establish LIVE LOCAL and advancing refreshes before judging delivery; an offline quiet UI is not failure evidence.
- Use the exact newly built executable for both first and second processes, record its hash, first PID, second argv/exit and first-process survival. Ensure older test app variants with the same bundle ID are closed. A visible exact URI preview is the runtime oracle; exit0 alone is insufficient.
- Close the preview and observe later advancing refreshes for a bounded quiet interval. Report “one preview observed, no recurrence during the observed window,” not universal exactly-once delivery. Use an inert URI and avoid Parse locally/payment execution.
- The old wallet-disabled loopback node is a connection/polling fixture only. It does not qualify current node/validation behavior. Direct CLI second-instance delivery does not qualify LaunchServices handlers, cold-start, Windows/Linux, the other requested Atlas cases, or a release.

No product/source/build/cache changes, no runtime execution and no publication by this reviewer. Only this report written. Parent remains responsible for the native observation, cleanup and final claims.
