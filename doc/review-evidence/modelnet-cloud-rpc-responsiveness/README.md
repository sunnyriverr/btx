# ModelNet cloud RPC responsiveness — paired Linux qualification

**Same maintained native test: baseline exit 2 (two contract violations), candidate exit 0.** An ordinary helper call during a 2.05-second paused upload changes from 2050.942 ms to 0.210 ms. Network status answers in 0.989 ms with cloud_storage_busy=true; four cloud-only calls promptly return HELPER_BUSY.

## Code and one-command reproduction

[Focused product commit ebb0942b2f8a57c1b99ba0f6d5d89a8604f9b0f3](https://github.com/sunnyriverr/btx/commit/ebb0942b2f8a57c1b99ba0f6d5d89a8604f9b0f3), parent release-0.34.17@a97af7b3f379e33e3ec65db948468d875ade2841. Two files only:helper.cpp and the standalone POSIX helper regression. No prerequisite PR stack.

Build baseline and patched btx-modeld with the normal ModelNet/OpenSSL configuration, then run the same script from the product commit against each binary:

```sh
BTX_OPENSSL=/path/to/compatible/openssl python3 contrib/devtools/test_modelnet_cloud_responsiveness.py --helper /path/to/btx-modeld --out /tmp/cloud-check-NEW
```

The output directory must not exist. Expected exits:2 for the baseline responsiveness defect,0 for the fixed contract,1 for setup/healthy-control failure. The fixture owns its temporary helper, two-second origin barrier, credentials and cleanup. It uses a controlled loopback HTTP origin, not a real S3 account or authentication qualification. It is a standalone maintained regression, not registered in the default test runner.

## What passed

- Hello/status complete before origin release; status does not claim an unavailable cloud snapshot.
- getcloudstorageinfo, setcloudstorage, setmodelstoragepolicy and detach are refused while upload owns the store. Exact config and budget bytes remain unchanged.
- Identical set/policy keys work after release; duplicate replay is safe. Upload/re-upload objects are262,144 exact bytes with SHA-256 0c40120eeb6a93be2f6cfffb88e3a6bd273b043b4254371413c0efff6847bd40, same artifact ID.
- Read counters progress1 → 2 and15 → 30bytes; configuration replacement preserves them and restart retains2 / 30. Two clean helper exits per phase, all HTTP handlers joined and owned container removed.
-46 existing cloud cases and seven selected first-run cases pass on the candidate. The cloud invocation intentionally filters36 non-cloud cases; it is not aggregate test_btx or the whole first-run suite.

[Qualification run 44275642974](https://github.com/sunnyriverr/btx/actions/runs/44275642974) uses [recipe888c6ff8648de226b523e8566a1169ea60ab96c1](https://github.com/sunnyriverr/btx/tree/888c6ff8648de226b523e8566a1169ea60ab96c1/proposal). Baseline execution is from [44274288368](https://github.com/sunnyriverr/btx/actions/runs/44274288368), reused unchanged. Final native test SHA-256 ae71ae5a6356f3a54b4954486136c032b163286c7c430fd310486282db2663e1 matches both phases and the product file.

## Exact scope and setup disclosure

Ubuntu 22.04 x86_64/GCC 11.4/OpenSSL 3.5.9 container on Ubuntu 24.04 host; retained 23ee567ea8a2d9cad8ca3264f8793e8371b3eb93 source/cache plus the exact helper/test repair. Relevant ModelNet source is unchanged at a97; publishing the same bytes on a97 is source applicability, not a fresh complete a97 build. The focused existing-test consumer uses normal test main/support libraries and is qualification-only. No native Mac/Windows, full node/GUI/WAN/peer/GPU/release or broader cloud-recovery qualification. Busy detach refusal is tested; this trace does not add a healthy-detach/restart claim.

The first qualification job stopped before any product compilation because Ninja could show only its glob/regeneration prelude. The corrected job explicitly freezes/configures the qualification graph and reuses the valid baseline proof; compiler/runtime flags and product/test bytes are unchanged. Build 341.225 seconds, 24 executed steps. See [pilot record](records/pilot-qualification.json) and [classification](records/first-job-classification.md). The known Boost JUnit CDATA framing is handled by the previously validated reader; raw XML is preserved alongside normalized XML and native exit 0.

## Evidence index

- [Paired machine-readable qualification](records/qualification.json), [baseline raw replies/timing](records/baseline.json), [candidate raw replies/timing](records/candidate.json).
- [Independent saved-evidence audit](independent-evidence-audit.json), [source identities](source-identities.json), [build log](records/build.log), [build plan](records/build-plan.log).
- [Raw cloud XML](records/cloud-suite.xml.gz), [cloud console](records/cloud-suite.log); individual first-run logs are in records/.
- [Artifact metadata](records/artifacts.json) and [download receipt](records/artifact-receipt.json). Records ZIP SHA-256 3fbbb45945d72ebca68e8615d3655ae4b51fa72e32626d37ec1c73b551710364 was downloaded and checked. Candidate binary/checkpoint metadata is retained until 2 December; those large ZIPs were not downloaded locally.
- [File checksums](manifest.json). Private test keys are synthetic; no production resources were used.
