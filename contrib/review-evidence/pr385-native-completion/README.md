# Native Linux remote-work completion for PR385

Candidate `d5be8de270fe262d273155ca4c03b86e62c09637`, parent `fd3a905fed3bc4943ad24372da032af4d29304a3`. The preceding commit changes only the maintained test file and may be cherry-picked separately from this evidence commit. Original scan fix and its existing tests are repch1c’s work.

Same harness, one run each on Alpine Linux/aarch64, GCC14.2, musl1.2.5, SQLite3.49.2: baseline direct completion/denials PASS, automatic scan FAIL at `fresh-database: completion timeout, last maintenance_error=SEC_DATABASE_PREPARE`; candidate two cases PASS with five genuine signed endpoints. Endpoints are direct control, fresh-table work, work behind70wrong-host IDs, controlled wrap, and new work after Service restart. Output is exactly93bytes with checked SHA384. Both worker signatures and receipt/result/work/package/runtime/output bindings are checked. Unapproved and wrong-host scan work remain without run rows.

The baseline stops at its first failure; later baseline70-ID/wrap defects are not independently isolated here. Wrap uses an explicitly set/checked persisted cursor at an already completed ID while Service is stopped. It is controlled fixture setup, not a naturally sampled cursor. Candidate execution took6.571s; baseline12.203s includes the expected12s timeout, not a speed comparison.

## Reproduce the executed recipe

From this directory in a clone retaining both pinned commits, on the configured native Linux profile:

```sh
python3 bootstrap.py --repo ../../..
python3 assemble.py --work /tmp/pr385-review
cmake -S /tmp/pr385-review -B /tmp/pr385-review/build -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DBTX_SOURCE_ROOT=/tmp/pr385-review/source -DCRYPTO_ARCHIVE=/absolute/path/crypto.a -DJSON_ARCHIVE=/absolute/path/json.a
cmake --build /tmp/pr385-review/build --parallel 1
python3 run.py --work /tmp/pr385-review
```

Bootstrap recreates and hash-checks the exact immutable Git-source archive and baseline files used during execution. Assemble then checks every source/package input and the test patch. The raw native build/run was executed before packaging; the new bootstrap+assembly reconstruction is separately verified against that native identity catalog. It does not repeat the runtime.

Two native dependency archives are reused, not rebuilt in this run. Required SHA256 values are in manifest.json: crypto.a `9ffd1f34d9645eaa0fe2a097592fed8f0b999e2cf17b53de856a5f50ba19fc6b`, json.a `588eb4e5fedf47598db9cd548441dab629888ad8f1514e59cce6b2f4d6c2c439`. The [earlier dependency-build instructions](https://github.com/sunnyriverr/btx/blob/d12d7c3bcd3705954b70a2edb40d0c5c8e38a7c6/contrib/devtools/review-evidence/pr381-cap-proof/reproducer/README.md) name the official targets; these bytes were identified from the prior fresh384Linux build. Probe source is original and freshly compiled static. CMake requires both exact archive files; verify their hashes before building.

The unchanged384timing prerequisite is applied to both variants. Existing configured8MiB ELF GNU_STACK is explicit in CMake and both saved readelf outputs. This is component execution with that prerequisite/profile, not default-stack, whole-daemon, GPU, physical-multihost, other-OS or release qualification. No production implementation change is included in the test commit.

## Results and provenance

results/ contains original selected-case summaries with signed envelopes, aggregate checks, ELF output, build/configure logs and the acceptance receipt. Local private fixture keys are not published. Full local provenance/archive hashes are retained in that receipt. Source and binary identities are exact; original fixture paths in logs refer only to disposable test directories. AI tools assisted implementation and internal review; this is one actual native executor run per variant, not independent reviewer platform replication.
