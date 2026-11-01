PR340 protected-store capacity recovery — verified local candidate

Outcome
The final fix keeps the source connected when a requested background body cannot fit, delays its retry briefly, and stops fetching later background bodies while that missing body waits. Existing storage/pending/rate limits and all proof/activation validation remain intact. The exception is limited to requested uncovered background holes on a consensus node; other behavior is preserved.

Verified recovery
Same final four-case unit patch, exact34070e35da0: unchanged production source passes16-body and cap1 controls but fails the two unlimited-pending overflow cases. With the fix all four cases pass,813 assertions. The17th body is not stored or credited prematurely; no immediate re-fetch; after capacity frees and cooldown expires, ordinary SendMessages requests it, it validates and completes the17-block snapshot with authenticated work. A33-block fixture also proves later descendants are not fetched during that wait.

Seven adjacent cases pass,362 assertions, on the exact final focused binary: failed ExactReplay stays rejected; unsolicited background body does not get GPU time; ordinary background walk reaches its base; cap1/1-per-minute background recovery completes; normal budget-window retry, closed-window non-spin and pending-slot release work. The paced cap1 case reached its two-block base after121s. This is not a mainnet throughput claim.

Actual unpaced GPU/P2P before/after
Identical harness and exact private299 fixture in fresh strict-device Metal consensus nodes. Before: source disconnected, background116/active299, incomplete authenticated work. After: source connected, background299, active300, snapshot validated, all199 historical bodies101..299 have valid BlockChecked, authenticated work equals claimed0x25a. Completion at12.281s in this toy fixture. The full queue was exercised95 times, and body117 was re-requested and validated. Final validation sample uses full Metal with0 CPU GEMM/host XOF/device fallback. Snapshot loader/checksum checks remain on.
The earlier candidate already recovered, but requested1439 blocks and dropped1140 for capacity. Final root-first backpressure makes394 requests and95 drops in this fixture. These counts include setup requests and are not a production bandwidth estimate.

Controls that establish test sensitivity
Turning off strict cooldown makes the test catch immediate re-fetch. Removing only descendant backpressure makes the33-block case catch descendant fetch/root starvation. Same final test patch also reproduces the source disconnect against untouched340 production code. Expected failures are saved locally; the actual final patch is restored and passing.

Provenance and overlap
Source70e35da0 plus candidate-production.patch and tests.patch; pristine combined-patch apply verified. Normal fresh CMake btxd builds. Unit executable uses normal CMake main+peerman objects and normal libraries, not a completed full test_btx build. Clean unit checks need no private299 snapshot pin. GPU binary uses the same explicit299 block/UTXO/shielded hashes as the prior fixture; that test-only metadata patch is removed from current source. Per-run source, script and binary identities recorded.
No matching fix found in79 public open heads; final refresh unchanged. JPP fold2466ac8c still contains the disconnect branch (code read only). Its cross-platform CI report does not duplicate this specific overflow/device recovery evidence. No folded-tree CI or macOS LT self-test qualification is claimed.

Scope and status
AI-assisted macOS M4 toy-regtest evidence. Linux, Windows, production-scale replay and deployment remain unqualified. No consensus rules or production services changed. Original unrelated PR280 work preserved. Originally tested locally; now handed off as a fork branch at the author's request. No new PR. Independent review pending.


This branch contains exact candidate-production.patch and tests.patch applied to70e35da0. No private snapshot metadata is committed. The199-body GPU fixture required the recorded private299 metadata; those timings are not qualification of the branch as-built with stock snapshot pins. The four focused unit cases need no private pin. See DESIGN.md for quota-aware scheduling analysis and RETRY-EVIDENCE.md for the separate unchanged3401024-body log. No tests were repeated for this handoff.
