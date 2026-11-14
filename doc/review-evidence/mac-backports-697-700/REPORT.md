# Native Mac acceptance of #697–#700 — complete at scoped test level

JPP’s supplied backports have discriminating native Mac evidence. The node built successfully, four focused functional invocations failed before the repairs and passed afterward, and #699’s focused unit suite plus matched negative control completed. Valid peer-serving controls also passed. Nothing was posted upstream.

## Exact target and environment

Base `a5d1637facc925ff176507fae87fc2042940829d`, with the four supplied product/test patches combined; see `ci/patch-manifest.json` for original heads, authors and patch hashes. These are combined-candidate results, not four isolated-head builds. No product repair was authored here.

Native macOS 15 ARM64, image `20261104.0514.1`, Xcode 16.4, Apple Clang 17.0.0, SDK 15.5; admitted static OpenSSL 3.5.9 library hashes; Python 3.12.16. Release CMake profile, wallet/SQLite/ModelNet and Metal compilation enabled. Metal compilation does not establish actual GPU-proof execution.

## Results

| PR | Same-test negative | Candidate and legitimate controls | Scope |
| --- | --- | --- | --- |
| #697 | Healthy import succeeds; explicit `[INT32_MAX, INT32_MAX]` import loses its RPC connection | All four maintained cases pass: healthy import, explicit bound, oversized default keypool rejection, ordinary refill error with unchanged descriptors | Mac baseline assertion/stderr was not retained; do not claim an observed assertion string. Later baseline cases were not reached. No UBSan overflow proof. |
| #698 | First no-bloom filtered request and empty getblocktxn each remain connected and fail the expected-disconnect wait | Supplied scripts pass, including both filtered variants. A permitted bloom client receives both correct genesis merkleblocks; nonempty getblocktxn returns the exact genesis transaction; subsequent pings pass | Separate Mac witness-only negative was not run. Valid-serving control uses the same saved candidate binary, no mining or wallet setup. Tiny genesis serving is not a full light-client or throughput qualification. |
| #699 | Removing only its product hunk makes the identical new case fail two `ProcessMessagesOnce` checks; 35/37 assertions still pass | Full six-case denial-of-service suite passes 124/124 assertions, zero skips; new case executes exactly once | Temporary test-only source selection retains original main, fixtures, compile settings and library/dependency links. Full `test_btx` build/run remains incomplete. In the one-case negative, the five other cases are intentionally filtered out; they passed in the positive suite. |
| #700 | Invalid batch element inherits preceding `id: X` and JSON-RPC 2.0 fields | Both exact supplied batch assertions pass, including the notification/error case | Only the maintained new method is invoked; its baseline stops at the first ID-leak assertion. Full `interface_rpc.py` has an inherited later mining expectation and was not qualified here. |

One execution per selected configuration/control; existing JPP Linux evidence is attributed separately. Four functional candidate invocations pass without skips. No mainnet, full functional/unit suite, wallet-funds, real-Metal proof or release qualification is claimed.

## Build and binary provenance

- Run [43647289770](https://github.com/sunnyriverr/btx/actions/runs/43647289770): baseline node built in **409.85 s**, 233 actual edges; incremental candidate in **53.77 s**. All four functional before/after pairs are preserved and were not repeated.
- Baseline `btxd`: `88cffcc9c43ffbd1d642a65e14379b5015c18c46e4514df28378385247af6f62`.
- Candidate `btxd`, also used by the valid-serving control: `cf23b285507a6eed8d12b7b026e7987acee0e7f6c1f205eb9fd0d4cafdc393fc`.
- CLI unchanged across the paired builds: `9e88d7e256725d52828f76a61d6a360f57eeede43cdd92739ed22b57a1d4dcfe`.
- Successful continuation [43651249392](https://github.com/sunnyriverr/btx/actions/runs/43651249392): verified saved checkpoint, **12 actual focused edges**, **10.28 s** build. Six-case suite 2.85 s; matched negative 2.40 s; valid-serving control 4.01 s.
- Tested #699 candidate: `88445a838bea7545e698f5cf35a13b8c870b50b17d845167f84315b91458fca5`. Restoring the source repair and rebuilding reproduces this binary byte-for-byte.
- #699 negative binary: `1d03dcf464e90fa4739e5a30824d1caa6361cc844791ad9b76a8f78d4969e3e1`.
- Temporary CMake selection hash: `abeffe6bb3cb25846b87bd00c2140624fb156881c2fcf8865ff20324bc87be21`; exact overlay in continuation records. It changes test source selection/output name only, preserving assertions and production libraries.
- Valid-serving harness: `9fd3916a05273b79b1f0b73330b1c0307952ce789a405e07e15ae5fbce138a4c`.

Each run collection contains `result.json`, exact logs and a checksum-verified `collection-receipt.json`. See `completion-receipt.json` and `restoration.json` for retained artifact/cache identities.

## Setup failures and reusable lesson

The initial preflight rejected a normal manifest-recorded CMake symlink back into the owned source. The corrected restore admits only recorded links resolving inside that workspace; external/traversal controls reject. No product test ran in that first pilot.

My initial Ninja cost check counted only CMake’s two regeneration edges, understating the unit build. The actual full target was 2,655 edges; it stopped at its 20-minute bound with last progress **874/2655**. Objects were preserved. The fixture now explicitly configures the final test selection and uses CMake’s documented [manual-regeneration setting](https://cmake.org/cmake/help/latest/variable/CMAKE_SUPPRESS_REGENERATION.html) to expose the actual plan before compilation. A regeneration-only dry run is refused. This fixes the execution tool rather than adding another protocol rule.

Independent internal review checked the focused source selection, dependencies, acceptance counts, negative control and claims. It is not a second independent platform run.

## Closeout and next step

The four scoped Mac rows are complete. The full unit campaign remains explicitly unqualified. Hosted jobs completed; the Mac’s source/build caches, wallets and production were untouched. All large restores/builds occurred on isolated hosted runners, with saved objects retained.

Next useful action: a concise evidence handoff on the existing JPP backports, after the user clears the publication hold. Recheck heads and substantive coverage at that point. No repeated passing tests or new investigation is needed for this campaign absent a relevant source/review change. The EVM task remains parked, and peers retain their independent tasks.
