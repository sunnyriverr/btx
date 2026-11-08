# Runtime prerequisite reconciliation — raw result review

**Scoped PASS: all 31 affected/control cases pass.** Exact candidate `37472d88c1e0d7dd88ac92e1c698351a0a7e9bd7` normally builds/links with the compatible cache and no compiler-command change. Twenty-five previously failed selected cases now pass; six relevant controls pass. Full Windows unit acceptance remains incomplete.

Reviewer: Session 1 delegated child `current_windows_plan_review`, 8 November 2026 Brisbane. Read-only ZIP/XML/source/checkpoint inspection; no API, build, test execution or source/cache mutation by this reviewer.

## Provenance, cache choice and build

Independently recomputed raw archive SHA-256 `8338efefbaaf1fefc731a82c700d70942a87287cabd99118fdf4865c8ed4544f` (17642627 bytes), run `42413581374`, CI `02aeb8448f7d10f6246812a8474224b25a2d951f`. Rehashed all 50 command logs plus configure diagnostics/configuration artifacts against native records; all commands exit 0 without a budget stop.

All seven current/full source catalogs agree. Independently matched all 14318 catalog paths/modes/blob IDs against immutable candidate Git source. Clean build metadata names exact 37472 with `BUILD_GIT_DIRTY 0`.

The complete **5898-entry current compile table equals the correct-flags c660 cache table**. The native full plan is 26 actions, zero command invalidations. Actual ordinary `cmake --build` succeeds in **41.59 seconds**, with the real changed source/header closure and normal metadata/library/executable links. All seven maintained executables link. This supplies native evidence for the previously inferred cheap cache route; it does not use mixed flags or suppress a required global rebuild. Generated executable definitions identify real `.exe` target paths.

New test binary SHA-256 is `31e45f1d0f2aed4168982120596182b5268057e1b9806960f27a60c769906bdd`. Its checkpoint identity matches the recorded runtime binary. Checkpoint bytes independently hash to `531e8b4d407b20e3655dc443a147b02401c2c47b8f2eeec6bdf498ffcfaf78af`: **5885 objects / 12838 files**, exact candidate/current configuration, captured before units. Pre/post ordinary-build configuration and checkpoint profile configuration agree.

Saved metadata identifies new immutable cache `10173603864`, exact key ending `f67683b7...-42413581374`, with prior caches retained. This verifies metadata availability and archived native checkpoint provenance, not a remote payload redownload/rehash.

## Exact case results and reused baseline

Independently re-parsed the raw inventory: **15388 enabled unique registered cases**. The declared selection is exactly 31 unique cases in 31 jobs, all registered. For each raw run, announced count and entered-case count agree with selection; XML contains the selected case as passed, with no unexpected non-skipped case. All 31 final case outcomes are **passed**, not inferred from a suite total. Runtime campaign duration is **75.7 seconds**.

Independently walked the prior raw XML from run `42373148335`, exact 70f binary `97924211...`, and rehashed its corresponding log/XML identities. Exactly 25 selected baseline cases were non-passing: 23 aborted and two failed. These are the same four direct executable-path cases plus 21 credential cases, now all passed. The native failure campaign was not repeated.

The six passing controls are:

- Cloud and R2 environment restoration: 14 assertions each; previous/missing environment values restored.
- Native model-index parser/help case: 11 assertions.
- Real AHP CLI fail-closed JSON case: 31 assertions.
- Confine and filesystem-jail native-helper launch/cleanup cases: eight assertions each.

The two native-helper controls now have actual current execution evidence; the prior campaign had not reached them. The AHP API/Journey cases now pass beyond their former suffix-less existence failure, retaining real argv launch, exit/output and safety assertions. This review does not extend the result to unselected refusal cases.

## Scope, causality and cleanup

Candidate source includes the existing target-derived path/dependency correction, case-local Windows ENV credential fixtures and unchanged accepted #433 S3 cleanup adopted from 2f3b source. The two nonfake transport cases previously failed before credential initialization completed; their new results are **combined prerequisite evidence**, not proof that the ENV fixture change alone repaired transport. This is neither a full build of the combined release nor stock-source qualification.

Native finish verifies source, 6230 installed dependency files and preserved OpenSSL identities, empty owned-process sets, removed runtime data/short-drive mapping, and no captured checkpoint-file changes during units. These payload-retention checks are runner measurements; this review rehashed the archived checkpoint/records rather than all remote cached payload files.

No material claim correction found. The inherited `unit_summary.full_pass=true` applies only to the explicit 31-case selection; `full_unit_acceptance=false` is correctly retained. The other 15357 registered cases were not selected here, and earlier unresolved failures/timeouts keep their original scope. Record this result and retained cache without another passing-case campaign or upstream post. Full Windows acceptance remains open.
