# PR370 focused review closeout

The in-flight background-root exception is required; production b3774256 is
unchanged. Local test-only commit `5deb327871efbca832e1a4e420f76dad74ff6b41` on `codex/background-eviction-inflight-test` extends the existing
case rather than adding a parallel test. Prepared for JPP's proposed #340 fold;
code and evidence published for review; no closure or merge.

## Exact final comparison

- A real FetchBlock request for height40 is recorded in peer in-flight state.
  Root16 still has its live eviction tombstone and active budget marker.
- Same final test source on both binaries: `f736e536ff07c8211709d3d8dedb1f3268c99e8695cd52bd651ca595973b05a9`.
- b3774256: PASS3/3, 556 assertions each; root16 requested, background reaches40,
  snapshot validates, all40 HAVE_DATA/local ExactReplay flags, source connected.
- Removing only `&& !background_root` from the in-flight early return: FAIL3/3,
  all at the required root16 GETDATA assertion. No unrelated failure/timeout.
- Candidate four controls pass once: pressure cooldown, marker-present fresh
  downloads, non-bypassable capacity wait, foreground acquisition priority.
- Binary hashes and commands/results: summary.json, candidate/, mutant/.

## Scope and adverse setup results

macOS/M4 Release. Normal CMake libraries plus main/peerman/lifecycle test objects;
mock verification worker and null-socket serialization. Not full test_btx, GPU,
Linux/Windows, production-policy, restart or mainnet qualification. Existing
exact regtest1124 metadata remains in the source identically on both sides; this
case itself creates its40-block snapshot through the existing fixture. The
previous published native1024-body result is unchanged and was not rerun.

First fixture pilot omitted flushing the outgoing FetchBlock frame before using
the null transport to inject HEADERS; it asserted queued. Next pilot served the
snapshot-base body early and ended39 rather than40. Final responder holds that
real outstanding response until parent39; both versions use the same corrected
source. Pilot results are retained separately and excluded from the comparison.

## Scope additions for JPP

Keep hash-wide tombstones for this fold. A different netgroup with room may be
held off even when global store space remains. JPP's alternative needs a
requester-capacity check and is not qualified here. The root exception prevents
the demonstrated root hold, not every possible recovery stall.

Incoming farther bodies can still evict retained bodies. Our native1024-body
case fits one download window; mainnet ranges spanning tens of thousands of
blocks remain unqualified. No throughput/backpressure redesign is claimed.

JPP and repch1c's independent Mac results remain their evidence, not ours.
Existing JPP fixture/prerequisite credit and Sunny authorship are preserved.

## Handoff boundary

Draft HANDOFF.md approves folding b3774256 plus the test-only follow-up, with
scope limits. The scoped handoff accompanies this publication. Keep PR370 draft/open
until JPP's adopted commit, source bytes and authorship can be checked. No new PR.
