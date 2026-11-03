# PR386 owner-revocation regression

Patch applies to b1be792041f9337b4d8e1156f8b6aa76b8e09277. Credit: repch1c's review comment6592257368 supplied the missing maintained scenario and independently demonstrated the continuation's sensitivity. This work adds coverage; it does not discover another product defect.

The native source's default CTest entry still runs every case. For bounded focused execution, argument2 selects one exact case; an unknown name exits2. Argument1 is an absolute output JSON path, whose parent must be absent or private0700.

## Clean reviewer recipe (provided, not executed in this resource-limited workspace)

Use a separate clean checkout at the exact commit above, apply candidate.patch, and build only the native component target:

```sh
git apply /path/to/candidate.patch
cmake -S test/util/model_security -B build-channel-review -DCMAKE_BUILD_TYPE=Release
cmake --build build-channel-review --target channel-recovery-tests --parallel 1
build-channel-review/channel-recovery-tests "$PWD/build-channel-review/owner-results/target.json" owner-revoked-active-freezes-once-and-unrelated-permit-survives-reopen
build-channel-review/channel-recovery-tests "$PWD/build-channel-review/quarantine-results/target.json" recovery-still-checks-owner-candidate-and-canary
```

On macOS a modern SQLite development library may need explicit `-DSQLite3_INCLUDE_DIR=... -DSQLite3_LIBRARY=...` configuration. This execution used Homebrew SQLite3.53.4. No Stream heap change or worker prerequisite is needed by these main-thread cases.

Both selected cases should pass. For the first sensitivity control, remove only the following line in lifecycle.cpp, rebuild that same target, and execute the identical owner case:

```cpp
if(!rollback&&row[4]=="frozen"&&row[3].empty()&&acknowledged)continue;
```

Expected failure: `repeated owner-revoked Tick revoked unrelated new permit`; this occurs after the initial safety controls. Restore that line before the second control. Replace only `row[1].empty()||active_invalid?"frozen":"active"` with `row[1].empty()?"frozen":"active"`, rebuild and execute the identical quarantine case. Expected failure: `invalid active appeared recovered after candidate quarantine`. This second failure describes public lifecycle phase; independent Broker eligibility still refuses the invalid old capsule.

## Actual local entry point

`python3 run.py` is a retained-workspace partial relink using existing read-only native component archives from channel-freeze-recovery/execution/native-build. It verifies their exact hashes against the prior native-integration.json, assembles isolated exact Git source/header inputs, compiles the final harness once and the two precise known-bad lifecycle objects, then runs the two focused cases and their matched controls once. It enforces max12MiB total owned files and1.25GiB free disk floor. It refuses to overwrite an existing build/results directory. This is not a portable clean-build qualification; the clean recipe above remains unexecuted.

The owner case destroys the original Active/Lifecycle/Broker/Database scope before constructing the reopened Database. A retained Temp object holds original fixture cleanup ownership, preserving absolute local-config paths. It tests Database reopen and direct Broker reads, not Service boot/maintenance, native workers, Linux, Windows, full daemon, concurrency or production.
