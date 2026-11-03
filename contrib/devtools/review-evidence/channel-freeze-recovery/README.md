# Channel freeze/recovery regression

Code commit `b1be792041f9337b4d8e1156f8b6aa76b8e09277`, based on `fd3a905f`; branch `codex/fix-channel-freeze-recovery`.

Repeated handling of an expired retained active capsule revoked fresh unrelated permits and cleared a valid staged successor. The repair acknowledges a handled current failure while continuing owner/eligibility/rollback checks. Broker policy is unchanged. Original finding: [Jpp-matata, #275 item5](https://github.com/btxchain/btx/pull/275#issuecomment-6433856983).

- Matched native Mac component harness: baseline4/6, candidate6/6; the two failures are actual unrelated permit use after repeat/Database reopen and legitimate successor recovery.
- Fresh candidate component build: CTest `security-channel-recovery`1/1, underlying6/6. This is distinct from the matched partial-relink comparison.
- [Execution report and limits](execution/REPORT.md), [baseline](execution/results/baseline.json), [candidate](execution/results/candidate.json), [native build/test receipt](execution/native-integration.json), [test command](REPRODUCE.md).

The product branch contains the actual regression source and CMake target. Evidence here is selected text provenance/results; no binary/cache/database/private key is included. Full synthetic signed-envelope snapshots remain local, with exact hashes/counts in raw-record-catalog.json; the regression generates new snapshots when run. Internal review audited those snapshots, but is not another native execution or human replication. Detailed local paths are normalized; original/published hashes are in normalization-manifest.json. Historical full manifests may name files outside this selected public catalog; SHA256SUMS describes the files actually published here.

Scope is macOS arm64 component admission/state transitions with signed synthetic canary receipts and explicit historical monotonic API times; actual descriptor-scoped reads run, but no Service/native sandbox worker or model/inference runs. Database reopen is not a process/guard restart. No Linux/Windows/full-daemon/release qualification. Earlier test setup/control/policy pilots are disclosed in the execution report; final matched inputs establish the result.
