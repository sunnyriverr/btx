# Catalog metadata recovery — Linux observation

**A surviving complete export can recover the catalog through normal importmodel; bare cloud objects do not restore metadata with no peers.** Exact identities/bytes and restart passed for the reimport control.

Start with [REPORT.md](REPORT.md), then [result.json](result.json) and [native-result-receipt.json](native-result-receipt.json). [SOURCE-TRACE.md](SOURCE-TRACE.md) distinguishes source routes from executed behavior. [SHA256SUMS](SHA256SUMS) pins these files.

Executed run: https://github.com/sunnyriverr/btx/actions/runs/43651794115

The run used retained PR707candidate helper bytes on Ubuntu24.04 and real MinIO PIECE_OBJECTS; it was not a whole-current-daemon/release test. Source-path comparison with f40eb37a and remaining limits are in the report. Fixture credit: repch1c / issue613.

The exact run wrapper/base fixture/driver are included: workflow.yml, run.sh, base_minio.py and catalog_recovery.py. run.sh stages the base as feature_modelnet_minio.py. expected.sha256 and dispatch-receipt.json pin inputs; hosted artifact availability/expiry is recorded. Replaying the included recipe independently has not been claimed.

Remaining decision: define whether cloud recovery requires a retained export/manifest peer or should have a supported metadata backup/restore workflow. No restore feature was built for this observation.
