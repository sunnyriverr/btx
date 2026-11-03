# Execution recipe and build limits

The delivered harness is exactly the source used for both binaries. The linked
component recipe was executed on macOS arm64 with Apple clang 17, C++20, -O2,
-DNDEBUG, -Wall -Wextra -Wpedantic -Werror, and Homebrew SQLite.

`build-run.json` contains every command, candidate/reused-object source hash,
repository dependency check, crypto/UniValue archive hash, SQLite/compiler
identity, binary hash, exact per-case aggregate checks and resource observations.
Only review workspace path prefixes are normalized to `${REVIEW_ROOT}`; raw
record hash is retained. Baseline and candidate results are separate JSON files.

The tested retained-workspace command was:

```sh
python3 work/btx-review-tools/store-quota-recovery/upgrade/build-run.py
```

`retained-workspace-build-run.py` preserves that driver. It assumes the original
review directory arrangement and documented prebuilt baseline objects/archives;
running it directly from this evidence directory is not supported. The local
source overlay contained baseline headers plus the three product source/header
changes. Baseline dependencies were verified against fd3a905f; only database.cpp
and trust.cpp were recompiled for the candidate, with the other 9 component
objects reused. Database layout is unchanged. Both links used the same harness
object. The post-run driver comment was corrected to acknowledge its two
short-lived race threads; execution code was unchanged.

For a different environment, compile this fixture with that environment's
baseline security component and crypto/UniValue/SQLite dependencies, then replace
only the candidate database/trust objects and matching database header. Such a
clean or other-platform build has not been qualified by this result. No generated
private keys, test databases or binaries are included. Expected baseline statuses
are PASS/FAIL/FAIL/PASS; both progress failures must be SEC_OBJECT_QUOTA. Candidate
statuses are four PASS. Both injected late-write observations must specifically
change from baseline SEC_OBJECT_QUOTA to candidate SEC_DATABASE_WRITE.
