# Catalog deletion: supported recovery and cloud-only limit

**Result:** re-importing a surviving complete model export restores identical model/artifact IDs and exact bytes, including restart. With no catalog, original, checkout or local pieces, cloud payload objects alone do not restore the model through ordinary getmodel with no peers. Remote bytes remain intact.

## Executed observations

1. Healthy import, upload, retrieval and export matched the independently reconstructed MinIO bytes.
2. Stopped the disposable helper, deleted only catalog.json, restarted it. getmodel returned WAIT_FREE/not_local, export NOT_FOUND. Committed-piece SHA256 map and remote bytes were unchanged.
3. Deleted the original input, then called importmodel on the surviving complete checkout with publish=false and pin=true. Model/artifact IDs matched; exported bytes matched; retrieval and export still passed after helper restart.
4. Stopped the helper; deleted catalog, checkout and committed artifact. The original input was already absent. After restart, getmodel stayed WAIT_FREE/not_local with peers=0 and export stayed NOT_FOUND, while MinIO still held the exact original bytes.
5. Restored the original fixture input and imported normally. The same identities, exact export bytes and another restart passed.

No JSON flags were edited. Catalog/file deletion is explicit fault injection while the test helper was stopped, not an observed crash or power-loss test. These observations reuse the real-MinIO fixture from repch1c / issue613; no FakeS3 fallback.

## Exact provenance and execution

- Run: https://github.com/sunnyriverr/btx/actions/runs/43651794115
- Executed wrapper:74dd60cf8744e480b593616ad5d9f64d60b40b1f; required native test exit0 and result assertions pass.
- Ubuntu24.04 x86-64; one4,163-byte SafeTensors fixture; PIECE_OBJECTS;64MiB helper quota.
- Retained PR707candidate helper SHA256214de8dad821fc433bad8c31c558c7e1958efdcb83909aee9daafbc5324a6c1d. Original8d6node/CLI acted as RPC proxy; no rebuild.
- Result artifact14136486929, SHA2561220ccae60b50a0c6dc8e26aaab4741909ab16df1660747a9cbcc07dcfee94c8, expires2026-11-28T23:09:58Z.
- native-result-receipt.json, source-binary-reuse.json, dispatch-receipt.json and source-provenance.json pin the binary/source/fixture/results. SHA256SUMS pins this package. run.sh/workflow.yml record the executed hosted recipe; local replay of that recipe was not performed.

The trace began at swapnet-v2/a5d1637f. During final review upstream advanced to f40eb37a and incorporated707. Current helper.cpp equals the tested candidate product; the traced catalog load/persist/import/materialize/install, store materialize/index, helper_network02 and manifest verification paths match as recorded in final-review.json. The newer quota-feasibility guard/ArtifactBytes refactor was not natively qualified here. This is not an untouched whole-current-daemon run.

## Scope and interpretation

SOURCE-TRACE.md records existing reimport/verified-peer-manifest routes and the cloud entry requirement. An index/search hit or raw saved manifest is not a demonstrated catalog restore workflow. A complete export is already a usable recovery input; the cloud-only case needs an explicit metadata-retention/restore contract before a new mechanism is designed.

Not tested: native peer/package restore, malformed catalog, multi-file/large models, Mac/Windows, SOURCE_FILES recovery, WAN/R2, model execution, power loss, full suite or release. The inherited fixture's generic layout-success log does not enlarge this specialized driver's scope.

Initial43651624629pilot failed before executing product behavior because its specialized class lacked required forwarding methods. Corrected driver/binaries are identified above; pilot-disposition.json records the setup failure. Offline result handling rejects11missing-result cases. No product patch accompanies this observation.
