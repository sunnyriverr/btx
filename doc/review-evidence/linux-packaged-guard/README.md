# Linux packaged guard sibling — qualified fix

Fix `974f7f8340174004cf836dff9f278c54b5160f31`, base `0ac06fd23b4a62038963fb29f1c77ab26d7a1346` (release-0.34.16). Linux-only packaging adds a regular hard-link sibling at libexec/btx-guardd. Existing binaries, runtime discovery, symlink rejection, child environment and authority rules are unchanged.

## Executed evidence

Native Ubuntu24 x86_64 run [42372485349](https://github.com/sunnyriverr/btx/actions/runs/42372485349), fixture74b335ccebc9f3ca83d48bca75b8dfc8a6aa6e2f. Same case SHA256fbf9344056029eac75bf5e809a7d301eef978e3969e91ace1408d8425732365d:

- Original official586 package: exit1, only guard readiness fails; both boots report GUARD_EXECUTABLE_ABSENT/SEC_GUARD_NOT_READY.
- Production-staged regular sibling added: exit0,59checks pass. Actual guard PIDs13607/17492 are direct children of the nodes, execute the sibling and answer status IPC, with fresh guard_boot after restart and20ready observations.
- Symlink substitute: exit1, only guard readiness fails. Across all three phases/sixboots,60ordinary node/helper health observations, model-identity persistence and normal teardown pass.

All127original package file hashes remain unchanged; one regular file is added with original guard digestede4ca9e7cb6e2855345489321989a12f64cd1c0277c448e587c6e8cbcb864b2. No binary rebuild. Archive asset720210208,158893635bytes,SHA25658657765b5ac41252c44913f56c61247b781149fd21ed79374aedade67805ba1. Source mapping is Numair's, not a reproduced producer build.

Full maintained17test packaging suite: same final test gives1newfailure before/all17pass after, on MacPython3.9 and native Linux. Synthetic binary fixtures explicitly stub ship gates there; the native production staging uses realELFs and unstubbed gates. The maintained regression checks actual TAR extraction, regular/no-symlink/content/mode/wrapper properties and deterministic output for Linuxx86_64/arm64 configurations. It does not execute nativeARM64.

## Recipe and retained files

For the maintained regression, run `python3 test/util/package_release_archive_test.py` in the fix branch. To reproduce the paired unit outcome, retain the new test while reverting only the six-line packaging addition.

The exact hosted recipe is in scripts/workflow.yml, scripts/run.py and scripts/case.py. The workflow checks out source0ac and installs libevent-dev,libsqlite3-0,libzmq5,libgomp1. Its original CI payload also holds the two product files at the hashes in scripts/code-identity.json under contrib/devtools/guard-package-repair/payload/. Those same files are in the focused product commit. It runs maintained-before, before, maintained-after, after and symlink-refused, propagating unexpected failures. Current package/source hashes are pinned; archive replacement intentionally causes refusal rather than testing different bytes.

See native/verification.json, native/result.json and native/collection.json for results, commands and artifact/file hashes. Phase directories retain raw RPC/process records and console logs. Original artifact SHA2569a989b25152c5dcf9411009a8722e9cbd0c724f939b83babaeb7940519e4e1d3. No cookies, private identity stores or generated private keys were retained. All phase runtime directories and owned processes were removed without harness fallback signals; no cache was used/saved.

## Limits

One native paired campaign, offline wallet-disabled regtest, short health windows. Native testing overlays the production-generated addition onto the complete official installation; it does not extract a newly built full release archive. TAR hard-link extraction/reproducibility is covered separately by the maintained synthetic regression. No model execution/inference/transfer/GPU, protected workload, full node/security suite, long-duration uptime, nativeWindows/macOS or release qualification. Guard status explicitly retains model_safety_proven=false and legacy_generatemodel_mediated=false. Internal source/records review is not independent native replication.

A local fixture setup error (Python3.9 lacks extractall(filter=...)) was corrected before final paired tests; final regression uses data_filter where available and otherwise only its own fixed trusted archive. No production safety check was weakened, and no failed native pilot occurred.
