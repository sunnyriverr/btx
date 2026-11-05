# Automatic-download consent and ordinary restart

**Tested PASS on unchanged `666673a3`: live opt-out cancels active automatic acquisition, persists across ordinary restart, and permits valid manual work and later automatic completion.**

[Native run 42017579549](https://github.com/sunnyriverr/btx/actions/runs/42017579549). Exact product `666673a3153225ba264c7870e0e82e354df86765`; executed fixture `4a15f7ad7a053ed3e8619c5aa07e8da2c034dcd3`. The fixture reuses the maintained LAN readiness/verification, profile-control and paced-retrieval test machinery. It is a new scoped integration fixture, not a run of the entire existing suite.

## Observed sequence

| Observation | Result |
| --- | --- |
| Actual automatic data before withdrawal | At 9.736 s a running job had one 4 MiB committed piece of a 71,303,243-byte model, incomplete/unverified catalog state and durable automatic=true origin. No manual request initiated it. |
| Live policy applied | At 9.748 s follow=false, preserve_rare=false and seed=off were visible, retaining 1 GiB quota. The job was still running: saved/queued acknowledgement was not mistaken for termination. |
| Cancellation and quiet storage | At 26.100 s the job was cancelled with last error automatic acquisition disabled by local policy. The same piece remained through four fresh publisher observations. |
| Ordinary restart while disabled | At 42.767 s saved/live disabled policy agreed; no matching jobs or new pieces appeared, despite three fresh authenticated source observations. |
| Manual positive control | A different 3,145,801-byte FREE_ONLY model completed while automatic consent remained off. Source, manifest and assembled-piece SHA384 agreed; original partial model stayed unchanged. |
| Consent restored | At 120.678 s the original model completed automatically through a new job. All 18 pieces total 71,303,243 bytes; source/manifest/assembled SHA384 matched. |
| Cleanup | Ordinary shutdown; finalizer found no owned processes, sent no signals, left none and removed its runtime. |

[Raw observations](raw/consent-observations.json), [framework test output](raw/consent-test.log), [native commands/results](raw/result.json). All 37 original raw text records are preserved as readable files: [mapping and original hashes](raw-records.json). Four identical source catalogs share one physical file. This evidence does not depend on the expiring Actions artifact or a ZIP reader.

## Platform and source

Ubuntu 24.04 x86_64, GCC 13.3.0, CMake 3.31.6, Python 3.12.3 and private OpenSSL 3.5.9. Fresh root build of btxd, btx-modeld, btx-guardd and btx-cli, Modelnet ON, wallet/GUI/units OFF. Release configuration explicitly overrides C/C++ to O1/NDEBUG. Root build 1693.35 s; one fixture run 122.02 s. Actual [generated compile commands](raw/compile_commands.json), [build graph](raw/build.ninja), [configuration](raw/CMakeCache.txt), [binary identities and command outcomes](raw/result.json) are retained.

All 14,309 tracked product files/modes matched accepted Git blobs before build, after build/test and at finalization. All four source catalogs have SHA256 c8497991392e27c28ffe00a22284413fb2863f1b9474a4a191dc95a11e5be2e0. No product patch or rule change was used. Fixture SHA256 286cca5763f1e69af390f7e0ee45fa5eeb1df4c7942a36635da104dbaab0f3b4.

## Reviewer entry point

Exact executed controls: [fixture](controls/feature_swarm_consent_restart.py), [runner](controls/run.py), [workflow](controls/workflow.yml), [plan](controls/plan.json). The executed invocation is recorded in raw/result.json. Normal reconstruction with matching native binaries and source framework:

```sh
PYTHONPATH="$PWD/test/functional" python3 contrib/devtools/automatic-consent-restart/feature_swarm_consent_restart.py --configfile=/path/to/build/test/config.ini --tmpdir=/path/to/new-disposable-runtime --result-json=/path/to/result.json --portseed=41725 --nocleanup
```

This normalized command is a reconstruction recipe, not a second run. The fixture needs room for two 68 MiB stores/source data plus a separate 3 MiB control and fresh regtest data; it never executes a model or spends. Its 400 s alarm and 420 s outer deadline own only these disposable processes. Use an empty temporary directory, not production data. The tested controlled runner additionally checks source and binary identities, installs exact prerequisites and performs final cleanup.

## Limits and interpretation

Two same-host native default-owned helpers, a configured publisher contact and LAN discovery enabled. Automatic retrieval selected the same-host LAN address; manual control used configured loopback. This is not a loopback-only automatic transfer or physical-peer qualification.

Restart occurred **after cancellation settled**. No queued/running-job replay, abrupt crash/simultaneous teardown, instantaneous zero-wire-byte boundary, model execution/GPU, other platforms, full suite or release qualification is established.

After restart bytes_verified=true coexisted with incomplete=true/complete=false and one piece. Completion always required both flags plus final independent digest verification. No separate defect in that presentation field is claimed. Final job bytes_committed=74,449,044 includes the separate manual model; it is global storage, not unique journey/network bytes or proof old pieces were never requested again.

No product repair is indicated by this observed workflow. Existing copyright/source attribution in the reused tests remains intact; this handoff supplies integration evidence, not a feature or policy change.
