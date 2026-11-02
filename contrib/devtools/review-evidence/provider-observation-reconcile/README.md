# #338 item21 — corrected local provider projection

Use code commit0670054b on codex/modelnet-local-provider-projection, based oncbf65894. This replaces eaffe632's per-action invalidation. Apply the combined change once tocbf, or inspect followup.patch relative to the earlier helper candidate; do not stack both whole patches. Original report and independent review: repch1c. Sunny River's prior authorship retained.

The fix stores only remote historical observations. CurrentProviderObservations adds a transient local provider from the current catalog seeded/incomplete flags at each existing observation consumer. Every real unseed or removal is therefore reflected on the next read, including the reviewed safety-report path. Remote records/ranges/timestamps remain historical, not claimed live. Local last_seen is now local observation time. This changes no serving admission or remote expiry policy.

Actual Mac/M4 helper comparison, one run per variant: rebuilt prior eaffe632fails5safety-view checks and passes22controls; revised helper passes27/27. Both use the identical reproduce.py/rpc_util.py. They cover reportmodelmalicious, three prior cleanup APIs, reseed, unrelated seeded model and restart. getmodeleconomyentryalreadycounts0before; it is a control, not another reproduced failure.

projection-test.cpp compiles the exact helper projection body with narrow adapters: remote partial flags/ranges/relay/timestamp and map nonmutation pass; modeled incomplete local state stays incomplete. This is not an actual peer transfer or actual catalog MarkIncomplete execution.

REPORT.md and REPRODUCE.md give the complete scope. Build identities/commands are the actual private full-helper-TU compile/relink against identical existing CMake libraries, with local paths sanitized. Not a clean full-project build. Linux/Windows, real peer transport, each inbound/campaign/admission/MarkIncompleteworkflow and concurrency stress are not executed. All changed APIs are shared C++20/STL/catalog paths; lock order reviewed.

To reproduce independently, build cbf65894with old eaffe632helper and with the corrected helper separately; place binaries under baseline/ and candidate/ beside these scripts. python3 reproduce.py baseline should record5expectedfailures; python3 reproduce.py candidate should record27passingchecks. Inspect JSON verdicts; process completion alone is not test success. Fresh temporary catalogs are cleaned by the scripts. Component commands are in REPRODUCE.md. No source model execution or GPU is needed. No original catalog, helper identity, credentials, wallets or binary dependencies are included.

Evidence is a separate commit above the exact code commit; product bytes unchanged during packaging. Public health metadata fields are omitted and absolute paths sanitized; behavioral results retained. The historical private report describes its capture-time status, superseded by this authorized publication.
