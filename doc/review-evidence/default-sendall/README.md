# Sendall default-list admission evidence

Proposed change: one line in test/functional/test_runner.py on release-0.34.17 371013d61dc124a363521df5b94e97f64d2464f2. Existing descriptor sendall test joins BTX_BASE_SCRIPTS; PQ-specific entry retained. Default230→231, ALL/explicit/extended selections unchanged/no duplicate. Candidate selector edit source-reviewed only, not executed as the default matrix.

Native proof: https://github.com/sunnyriverr/btx/actions/runs/43988284962, workflow3f82acfdb4769620fb7345873a84011f8bc0c4e9, existing product371013d6 binary9e2db736…/b58bd816…. One normal-runner descriptor script/24existing scenario calls/zero skips PASS143s;170.04s cache/controller,47.05MiB measured scratch. No rebuild; static restore/entrypoint/CSV/log/hash/bounds/shutdown/data cleanup verified. Ubuntu24.04 x86_64/SQLite descriptors/ModelNetOFF/economic CPU regtest. See qualification-receipt.json, native/ and build/.

Initial43987710758 stopped beforeBTX/test on missing libevent_extra. Package-only setup correction then one native invocation; initial qualification and correction receipt retained. Synthetic controller checks are not product coverage.

Published log/receipt copies redact workspace/home paths, loopback/bind addresses and test authentication strings. MANIFEST.json records each original and published SHA256; originals were independently verified against Actions artifact14286148464 ZIP9ec43d34e2a79f9eff5ea8a167a73b041c0364a97d7d38d3cfdbb91de0660bd9 and its per-log index before redaction. This directory is a permanent sanitized evidence copy, not a claim of byte-identical unredacted logs. No personal wallet/keys/databases included.

JPP772 and repch1c's independent Mac/revert qualification support the existing test at their named revisions: https://github.com/btxchain/btx/pull/772 and https://github.com/btxchain/btx/pull/772#issuecomment-6915750161. Their results are separate from ours. No candidate default/full matrix/current ModelNetON/Mac/Windows/GUI run, repository coverage percentage or whole-suite timing guarantee. No new tests run to publish this evidence.
