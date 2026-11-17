# Cloud detach — verified Linux before/after

Code: [a4b26322e7ab632e72753d90c9139db1660c4465](https://github.com/sunnyriverr/btx/commit/a4b26322e7ab632e72753d90c9139db1660c4465) against `release-0.34.17@bd847e2b986722c1723b4cd60988d4f4908452d4`. One focused two-file commit; original ModelNet implementation/test history and attribution preserved.

The helper used to report `detached:true` after cloud.json removal failed, then reload the old origin. The guard returns `IO_ERROR` before clearing live state; normal/repeated detach and retry remain valid.

## Executed evidence

[Successful CI run](https://github.com/sunnyriverr/btx/actions/runs/44010192766), control commit4218f5a60b176dc9875a0603cba2b0809ed3f3cc. Ubuntu22.04 x86-64 container on Ubuntu24.04 runner, GCC11.4/OpenSSL3.5.9. Exact executed controller/setup/workflow/native fixture are included here.

| Same check | Baseline | Candidate |
| --- | --- | --- |
| Maintained `modelnet_cloud_tests/cloud_rpc_detach_removal_failure_preserves_origin_and_retry` | Exactly four intended failures: success return, missing IO_ERROR/message and cleared live origin | Passes within all40 `modelnet_cloud_tests` cases |
| Actual helper, UID65534, readable config under deletion-denied parent | Only truthful-error contract fails | All four grouped contracts pass |
| Helper retry/restart and valid controls | Complete with original false-success behavior recorded | Honest failure; identical retry; absent detach; detached after restart; three clean starts |

FakeS3 object bytes, budget bytes and unrelated sentinel remain unchanged. MIGRATE stays plan-only and automatic_spend_atoms stays0. [Machine result](raw/result-summary.json), [baseline XML](raw/baseline-unit.xml), [candidate suite](raw/candidate-cloud-suite.log), [native baseline](raw/baseline-native/native-result.json), [native candidate](raw/candidate-native/native-result.json), and their exact RPC calls/logs are retained. The named suite is not all unit tests.

## Reproduction

The maintained case belongs in `test_btx`; the native fixture is separate evidence, not default-runner coverage. `build.py` records the executed source/test overlay order: baseline current helper plus the new maintained test, then the exact two-file patch and candidate. Typical commands, shown as a reconstruction recipe with local paths substituted:

```sh
BUILD/bin/test_btx --run_test=modelnet_cloud_tests/cloud_rpc_detach_removal_failure_preserves_origin_and_retry --log_level=test_suite
BUILD/bin/test_btx --run_test=modelnet_cloud_tests --log_level=test_suite
# Run as an unprivileged user; do not use a production helper or model directory.
BTX_OPENSSL=/path/to/openssl python3 native-detach.py --helper BUILD/bin/btx-modeld --out /tmp/detach-results
```

Baseline is expected to fail the new regression and native truthful-error contract; candidate passes both. Fixture credentials are dummy values, FakeS3 only. The native fixture uses temporary model directories and checks clean helper termination. No node, wallet, peers or actual cloud account is used.

## Provenance and limits

[Manifest](manifest.json) pins code, scripts, source/binary hashes and original artifacts. Original qualification ZIP artifact14296707039 SHA256 `05616cd343fe7d02032a949d4ddc5b6af390bcfcb74bf8a3f360fb4520407fa7` was downloaded and verified. Raw result-summary omits only the large retained-checkpoint file-row inventory; the unmodified full result remains in that CI artifact. Checkpoint14296487760 is retained until1December2026; its large archive was not downloaded/rehash-verified locally. Its metadata digest is not a local archive verification claim.

The earlier run44008579886 stopped compiling the regression cleanup due to a missing BTX filesystem wrapper overload; no tests ran. The one-line std::filesystem::exists correction reused its saved build, leaving the product guard unchanged. The successful run above is the qualification receipt.

Not tested: full node RPC proxy integration, all unit suites, current Mac/Windows repair behavior, real S3/R2/WAN, concurrent cloud reconfiguration or release qualification. Internal source/evidence review is not independent platform execution. No claim beyond the actual Linux helper and named unit suite.
