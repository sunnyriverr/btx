# Item21 scoped candidate and evidence

Original lead: repch1c, btxchain/btx issue338 item21. Candidate/testing: Sunny River, AI-assisted. Based on swarm cbf65894. Product commit eaffe632; test packaging e160cd98. This evidence commit leaves product code unchanged.

Read REPORT.md for actual native macOS execution and limits. Native Windows/Linux execution and real peer-ingested expiry are not qualified. No OOM or network-outage claim. One final lifecycle run per variant: baseline fails five cleanup checks; candidate passes all17 including reseed, preservation and restart. Bounded distinct-ID phases add3776KiB on baseline and0on candidate; process RSS is not exact heap accounting.

REPRODUCE.md describes building/copying the two binaries and running identical harnesses. Commands in build.json are the actual local focused TU/relink inputs with local workspace prefixes replaced by placeholders; not a clean portable full-build recipe. Static library hashes and exact native binary identities retained. The runtime memory harness initially read hashes from build.json; packaged binary-identities.json contains identical values, with only that lookup path changed after execution. Other executed source bytes are retained.

Raw helper network identity/status fields and local absolute paths are omitted from public evidence. Behavioral checks, timings, memory samples and cleanup outcomes are retained. Pilots disclose the first client ENOTCONN shutdown error and preliminary pre-reseed-check candidate runs. They are not final passing results. The shared source/build and production were untouched by these isolated tests. No claim that this explicit-API candidate solves all remote lifetime or implicit catalog eviction paths.
