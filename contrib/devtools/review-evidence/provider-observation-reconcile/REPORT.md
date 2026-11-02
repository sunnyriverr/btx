# #338 item21 review follow-up — local observations derived from catalog

**Same actual-helper test: prior eaffe632 candidate fails5 safety-report checks; revised candidate passes27/27, including the earlier cleanup paths, valid seeded model preservation and restart.** One run per variant on macOSM4. Component tests preserve remote partial-provider metadata; actual peer ingestion/expiry remains untested here.

Review request: https://github.com/btxchain/btx/issues/338#issuecomment-6572932800. Repch1c independently verified the first three API paths and reproduced reportmodelmalicious remaining stale. Fresh338discussion and open-head comparison show no later equivalent fix in the public material checked; swarm stillcbf65894. This is a correction to that same finding, not a new unrelated investigation.

## Cause and minimal coherent change

The first candidate put cleanup calls at unhost/unseed/remove. The catalog also changes seeded state through safety reports/advisories, admission/campaign rules, partial/incomplete transitions and eviction/removal. Adding one callback at every mutation duplicates state ownership and makes the next missed path likely.

The revision keeps g_search_obs for remote historical observations only. It stops caching `local` during IngestCatalogIntoSearch. A single CurrentProviderObservations(cat,id) projection copies remote observations, finds the current catalog entry and adds a transient local observation only if seeded. Completeness comes from !incomplete, not an old cached value. Unknown reads still use find, never insert a map entry. All four existing helper observation consumers now use the projection: search result decoration, individual directory card, provider/availability/peer RPCs and economy/feed decoration. Prior per-action cleanup calls and their extra catalog recheck are removed in the combined correction.

This makes local observation state follow the catalog's actual current flags, rather than trying to promise independent liveness. A current seeded observation's last_seen is the local read time; remote timestamps/ranges/flags keep their prior historical semantics. It does not test disk bytes or transport reachability, add a new serving policy, enable partial sharing, change remote expiry/cap limits, or repair a serving path that might fail to update the catalog. Availability remains UNKNOWN where piece count is unknown.

## Call graph checked

- Explicit helper unhost/unseed/remove: Seed(false) or RemoveModel changes the catalog.
- reportmodelmalicious and applied inbound advisory: UnseedSafetyTarget -> Seed(false).
- DemandSeedIfDownloadable, admission rejection, helper_network02 import rejection and campaign path: Seed(false).
- Catalog MarkIncomplete(true): incomplete=true, bytes_verified=false, admission=FETCHING, seeded=false.
- Catalog partial import/upsert: incomplete=true, seeded=false.
- Catalog demand-seeding refusal and safety refusal: seeded=false; removed/evicted entries no longer Find.

All are covered structurally by the same catalog projection when those state changes occur. We executed reportmodelmalicious and original public lifecycle APIs; inbound advisory, campaign, admission, eviction and actual MarkIncomplete RPC workflows were not individually executed. That distinction matters. Existing safeguards and whether a path correctly changes its seeded flag are separate from this cached-view defect.

## Runtime comparison

Original side is the independently reviewed eaffe632 helper.cpp, rebuilt against identical existing CMake static libraries. Corrected side is cbf65894helper with this combined projection correction. Both full helper translation units compiled with the same existing C++20 Release flags, privately archived/relinked; this is not a clean full-project build. Exact source/binary/command/archive identities retained.

The same final reproduce.py imports three valid tiny SafeTensors fixtures. Both variants pass the existing unhost/unseed/remove/reseed/unknown-ID/UNKNOWN-availability controls. reportmodelmalicious correctly unseeds the third fixture on both. Before: local provider, complete availability count, peer count, search refresh and individual directory entry still contain the stale complete observation. After: all five clear. getmodeleconomyentry already reports0on the old candidate, so it is a passing control, not an additional reproduced defect. Another seeded model remains visible; restart preserves expected absence/presence.

Baseline:5failures/22passing checks. Revised:27passing checks. One run each, no invented repeat count. No model execution, GPU, public network or node/wallet required. Both owned helper processes stopped; temporary catalog/safety identities removed.

## Partial-state/read-contract test and platform review

projection-test.cpp compiles the exact candidate projection body with narrow ID/catalog/observation adapters. It verifies remote partial flags, relay status, ranges and historical timestamp survive local unseeding/removal; seeded incomplete state is represented incomplete; unknown reads and synthesized local reads leave the remote map unchanged. Native C++20 -Wall -Wextra -Werror compile/run passed. This is a component test, not a real peer transfer or actual catalog MarkIncomplete execution.

No new system headers/APIs or Windows/POSIX branches. Each projection caller already holds g_search_mu. cat.Find briefly locks the catalog and returns a value snapshot; this is the existing search→catalog lock order. There is no new callback from a held catalog mutex into the search mutex. Concurrent updates can linearize at the catalog Find; the next read observes the updated flags, without a delayed cleanup deleting a new seed. Concurrent stress was not run. Linux/Windows execution remains unqualified. Synthetic catalog cases do not establish local partial-serving admission.

## Disposition

This supersedes the old per-action cleanup implementation; combined.patch applies once tocbf65894, followup.patch describes the delta from eaffe632. Use the final combined source, not both whole patches stacked. Original report and independent feedback credit: repch1c. Candidate's prior authorship preserved.

Ready for one focused reviewer handoff with the corrected branch and same regression evidence. No further generic tests are needed before that review. The current work remains local pending delivery instruction; records/source/binaries preserved and wiki current.
