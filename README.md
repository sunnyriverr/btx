# Retained Modelnet campaign lookup

On macOS arm64, the same live Unix RPC test imported two signed search records and forced eviction at a test-only cap of two. The original helper returned `NOT_FOUND` by model ID while the protected release still resolved by release ID. The patched helper resolved it by both IDs. Both variants kept the unrelated model lookup and shut down cleanly. The test used synthetic local models, with no wallet, peer transport or default-cap load test.

Both helpers were built from d522af520f55067bd470fdcc0c246e3b4d3a26fc with AppleClang 17, static OpenSSL 3.6.3 and the same compile-time cap of two. The patch submitted to BTX preserves the production cap. The linked campaign-index fixture also failed before and passed after on Alpine Linux arm64. Jpp-matata authored the original #342 campaign index work.
