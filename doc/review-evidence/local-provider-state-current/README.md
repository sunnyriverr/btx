# Current local model-provider state

**The same final helper regression fails 13 stale-state assertions on accepted `666673a3` and passes all 45 with `5eb69ade`.** The 32 baseline controls pass too. This is actual disposable-helper execution, not a node, wallet, real model workload or network-serving qualification.

## Code and result

Base `666673a3153225ba264c7870e0e82e354df86765`; final head `5eb69ade93cf148edb693fa6dadbe54db9bccb17`, tree `00e2713910c925f831ca0752d2ab2bec1efd8f7b`. Product commit `95e5273822a64b79a1e0ba6e084d3575033a5b88` carries the previously reviewed catalog projection onto current source; the second commit adds four positive test guards. Only helper.cpp and the maintained POSIX regression change. Finding and independent historical review: [repch1c](https://github.com/btxchain/btx/issues/338#issuecomment-6577879589). Sunny River's original code authorship is preserved.

The helper cached local seeded state separately from the catalog. Removing that local writer and projecting the current seeded/incomplete flags at the four observation readers avoids missed invalidation paths. Remote historical observations retain their writer/content. This does not resolve all remote-cache expiry/capacity concerns in item 21.

| Final identical assertions | Baseline | Corrected |
| --- | --- | --- |
| Stale provider/search/directory state after unhost, unseed, removal and catalog-owned unseed | 13 failures | No failures |
| Whole final fixture | 32 pass, exit 1 | 45 pass, exit 0 |
| Each variant's two real helper lifetimes | Both stop gracefully with exit 0 | Both stop gracefully with exit 0 |

Controls preserve seeded provider metadata, positive seeded search/directory/availability/peer counts, the unrelated seeded model, reseeding, UNKNOWN behavior and genuine helper process restart. The catalog-owned transition uses the existing local reportmodelmalicious API on one tiny fixture. Hosting, following, discovery and external listeners are off. Fixtures are three small valid nonexecuted SafeTensors files. The economy-entry zero count already passes before and is a control, not another repaired failure.

[Final results](native/verification.json), [baseline assertions](native/baseline-result.json), [candidate assertions](native/candidate-result.json), [exact identities](identity.json), [patch](native/product.patch).

## Executed entry point

From the final source checkout, with a POSIX btx-modeld built for the revision being compared:

```text
python3 test/util/modelnet_provider_state.py --modeld /absolute/path/btx-modeld --result /path/result.json
```

This exact in-tree entry point was executed against both archived native binaries. [Baseline command](native/baseline-runtime-identity.json) and [candidate command](native/candidate-runtime-identity.json) record the actual paths, pre/post binary hashes and final script hash. To compare the accepted source, use its binary with the same final test script; the accepted source itself does not contain the new script. Expected baseline exit 1 means the assertion failures recorded above, not a setup error. The standalone script is not registered in default test_btx or the functional runner.

Executor: Alpine Linux 3.22/aarch64/musl, GCC 14.2. Existing CMake O1 plus common `-include cstdint`; the full btx-modeld target rebuilt affected dependencies in 834.3 seconds. Candidate build took 28.0 seconds: generated build-info, helper.cpp compile, archive and executable link plus glob checking. Only helper.cpp was recompiled. [Build profile](native/build-profile.json) and build logs preserve the actual flags and target. This is a retained build, not a clean/default full-node or unit-suite result.

The final follow-up changes only Python assertions. Both binaries are reused unchanged from the earlier pair; no C++ rebuild or new product behavior was introduced for that follow-up. Binary hashes establish identity, not reproducible builds. Executables and wallet/identity secrets are not packaged.

## Provenance and limits

The owner observed 14,309 accepted tracked blobs matching before baseline build; 14,310 final blobs match the final tree. The raw baseline full-tree audit was overwritten by the later audit. Its baseline match is an owner-recorded observation supported by the staging recipe and retained accepted helper snapshot, not an independently retained native whole-tree inventory. [Final audit](native/final-source-audit.json), [expected Git blob catalog](native/source-inputs.json), [accepted helper snapshot](native/baseline-helper.cpp), and executed [staging](native/stage_guest.py)/[audit](native/audit_guest.py) records remain. The latter two are records of the owner’s local staging setup, not portable reproduction commands. Code/binary/harness identities and all assertions are independently inspectable from these retained artifacts.

The initial 41-assertion pair is retained in prior41. Internal review found missing positive directory/aggregate guards; four assertions were added and the final 45-assertion pair ran once per same binary. All original outcomes remained unchanged. This happened before delivery and is not an additional C++ correction.

No fresh Mac or Windows, full node/test_btx/default-runner suite, GPU inference, real peer transfer, concurrent stress or release qualification. Remote metadata preservation has source analysis and precisely scoped historical evidence, not a new peer-ingestion run. The fourth economy/feed reader has source review; positive fourth-reader and every implicit catalog-transition runtime behavior are not claimed. A provider observation describes local catalog state, not proven remote availability or serving.

Four helpers in the final pair stopped gracefully; temporary fixtures were removed. The owner stopped the disposable VM after qualification. Earlier Mac/repch1c results belong to their historical revision and are not independent replication of this Linux campaign.
