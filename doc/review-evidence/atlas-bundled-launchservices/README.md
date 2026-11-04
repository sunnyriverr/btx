# Atlas bundled Launch Services evidence

[Result and limits](REPORT.md) · [Reproduction procedure](REPRODUCE.md) · [Measurement summary](summary.json) · [Artifact review](review/FINAL.md). This supports [BTX PR273](https://github.com/btxchain/btx/pull/273).

Exact tested target: e70c81f03b76c5e62712ebb51dfaac7d41295af2. Genuine generated Tauri.app, default dev.btx.atlas identifier/config; locked/offline Rust1.95.0 build, local ad-hoc signature, Mac26.5.1 arm64. The binary hash and generated bundle metadata are in app-identity.json.

Four accepted native UI cases: coldbtx, warm-repeat-btx, coldp2p, warmp2p. The extra initial warm-btx attempt is retained as ambiguous because its first Close action did not visibly dismiss; it is not counted as proof of either duplicated delivery or once-only delivery.

Launch/observation records are coordinator transcriptions of native accessibility/visible preview results supported by computer-control history. Raw AX, screenshot and video files were not archived. The user completed two native connection confirmations; LIVE LOCAL and exact previews were independently checked afterward. This is not a replayable unattended UI assertion suite or an independent second native execution.

Public records redact only private path prefixes to <review-root>/<user-home>. Their actual hashes and published sanitized hashes are in record-sanitization.json; input source/binary hashes remain unchanged. source-compare.json is a normalized subset of the upstream comparison, omitting unrelated author/API fields. README/REPORT/REPRODUCE are delivery documentation. Historical summary.upstream_post=false describes the prepublication measurement, not a claim that this evidence is unpublished.

No wallet/cookie values, production operator data, app audit contents or runtime binaries are included. This branch adds documentation/evidence only on the tested Atlas base. Prior real bundle/file-URL work is credited to [repch1c](https://github.com/repch1c); the earlier accepted direct-executable coverage was reused.
