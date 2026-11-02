# Item21 local-provider lifecycle correction — private candidate

**Same real-helper test: original fails five cleanup checks; candidate passes all 17 checks, including seeded-model preservation and restart.**

This is a narrow correction to repch1c's #338 item21 lead: local provider observations survive explicit unhost/unseed/remove; observation reads allocate empty map entries. It does not claim to resolve every remote-provider lifetime/capacity issue.

## Candidate

Based on current swarm cbf65894e6d61084527cd93e913a00c6794418dd, one product file, helper.cpp:
- Observation RPCs use find rather than inserting an empty map entry; read under the existing mutex without copying the provider vector.
- After successful explicit unhost/unseed/remove, erase only the `local` observation and erase its map entry if now empty.
- Recheck the current catalog under the observation mutex so an already-completed concurrent reseed is preserved.
- Existing remote-labelled observations and availability semantics remain unchanged; no arbitrary TTL, global cap, validation or monetary change.

Fresh open-PR/issue338 check still showed unchanged swarm and no equivalent public map correction. The preceding 97-PR coverage check is in ../priority-after-atlas/DECISION.md. Unpublished work cannot be excluded.

## Native test and evidence

Apple M4/macOS only. A private full helper.cpp translation-unit compile and relink for each variant against the same cached CMake libraries. Compile/link commands, source and binary SHA256 identities: build.json; static archive identities: link-inputs.json. This is not a clean full-project build or GPU qualification. Shared source, objects, libraries and binaries were never overwritten.

`python3 reproduce.py baseline` and `python3 reproduce.py candidate` run the identical final harness on isolated owner-local Unix helper RPC. Each imports two distinct valid SafeTensors fixtures and checks initial seeding, immediate unhost/unseed/remove, search refresh, two reseeds, preservation of the other seeded model, empty unknown-ID reads, UNKNOWN availability, catalog removal and restart. Baseline has five intended failures (stale local observation after unhost/unseed/remove and refresh); its other 12 checks pass. Candidate passes all17. One final lifecycle run per variant; no invented3/3 claim.

Separate identical retention.py sequences use20,001 unique IDs, repeated-ID controls,30-second idle and restart. Each response remains empty. See baseline-retention.json and candidate-retention.json for measured RSS and timing; RSS is a process measure, not exact heap instrumentation. No network service crash or OOM test. `-modelbind=off` is rejected by this baseline helper while its Unix RPC continues; no model TCP listener/peer was needed or used for this local test.

preservation.cpp compiles the exact candidate cleanup function with narrow catalog/id/observation adapters. It verifies removing `local` preserves two other provider labels, erases an empty bucket, leaves unknown IDs absent, and preserves a currently seeded entry. Native C++20 warnings-as-errors compile/run passed. This is a component preservation test, not successful real-peer ingestion. The earlier two-helper search timed out; remote ingestion/expiry remains unproved.

## Inspection and limits

No new OS APIs, headers or conditional platform code. Source inspection covered the shared STL/mutex/catalog paths and existing C++20 build flags. Linux and Windows compile/link/runtime have not been executed. Lock order is observation/search mutex then catalog Find, as existing IngestCatalogIntoSearch already uses; catalog mutations return before cleanup. Concurrent RPC stress and allocator-exact accounting not claimed. Catalog eviction and other implicit seeding transitions are outside this explicit-API correction.

Initial unguarded-candidate lifecycle results were positive, then review added the reseed check before the final run. Initial rapid-read memory pilots on both variants stopped with ENOTCONN from the test client's shutdown call. Final rpc_util.py allows ENOTCONN only at shutdown and still requires/parses the server response; both variants use this same client. Pilots are preserved under pilots/. They are neither successful final results nor product failure evidence.

## Disposition

AI-assisted candidate and tests. Credit repch1c for the original item21 lead. Nothing uploaded, posted, pushed or opened as a PR. Candidate is prepared locally with exact tested source. Next handoff, when authorized, should present this narrow scope once, with branch commits and evidence; reviewers decide remaining remote observation policy separately. All disposable helpers/model identities are stopped/removed; old production node remains retired, wallets and unrelated tests untouched.
