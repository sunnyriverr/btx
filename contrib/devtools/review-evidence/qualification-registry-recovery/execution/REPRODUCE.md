# Reproduce the focused registry recovery evidence

Product base: `cbf65894e6d61084527cd93e913a00c6794418dd`. `patch.diff` changes only `src/matmul/compute_qualification.cpp` and the existing native Boost regression file `src/test/compute_profile_tests.cpp`. The latter requires no CMake registration change.

The actually executed local component entry point is:

```sh
python3 run-component.py candidate
```

Run from this evidence directory, or pass its absolute script path. It compiles the full candidate qualification translation unit and exact native test bodies, links the identified read-only native libraries, and runs the five focused cases. The fixture adapter substitutes a disposable-directory fixture for BasicTestingSetup; it does not stub a tested product/API/filesystem/work path. The entry point checks exact prerequisite hashes and resource limits and removes fixture directories after each run. It was executed once on the final candidate, all five cases passed. No clean whole-tree/test_btx build is claimed.

The executed wrapper returns shell status0 when compilation/linking and case invocation complete, even if a test returns failure. Treat `all_passed` and individual statuses in the run manifest as the result. Perform this read-only artifact-validation step separately from native test execution:

```sh
python3 - <<'PY_CHECK'
import json
expected = [
    "toy_qualification_solves_verifies_and_rejects_replay",
    "qualification_rejects_bounds_expiry_and_corrupt_registry",
    "qualification_quarantines_non_object_rows_and_recovers_empty",
    "qualification_quarantine_failure_preserves_source_and_reports_error",
    "qualification_quarantines_invalid_field_types_and_schema_overflow",
]
d = json.load(open("candidate-run.json"))
assert d["all_passed"] is True
assert [t["name"] for t in d["tests"]] == expected
assert all(t["exit_code"] == 0 for t in d["tests"])
print("candidate result: exact five cases PASS")
PY_CHECK
```

This aggregate assertion was executed against the retained candidate manifest. It validates recorded results and does not rerun a native case. The retained runner docstring still says four cases from the initial checkpoint; the final selector actually invokes the five listed below. Its executed bytes/hash are preserved.

Local prerequisites: macOS arm64, the retained `pr362-admission/build` native libraries/headers from source `dabe7981c6cb12d7f98c9567d5035225bd6fd8a1`, AppleClang17/Command Line Tools SDK, Homebrew Boost and libomp, all identified by `inputs.json` and retained original build identity. No installation/download is performed. The recorded input paths are local artifact prerequisites, not a portable promise of a clean build on a new host. `provenance.json`, dependency manifests and linker maps distinguish the fresh exact-base registry TU from reused libraries. The archive's old registry object is not selected by the linker. The package retains required source/header projection and baseline/candidate product bytes; `prepare.py` is an archival extraction aid, not a step to run over the final candidate.

The executed baseline was staged before the final candidate:

```sh
python3 run-component.py baseline
python3 run-component.py baseline-fields
```

The first invocation preceded addition of the malformed-field case and ran the initial four exact test bodies: two controls passed, null-row recovery and rename-error reporting failed. The second invocation used the final appended test TU and ran only the newly added malformed-field/oversized-schema case, which failed as intended for both payloads. The original four body bytes remain unchanged in the final TU. Initial script/source/input hashes and logs are retained in `initial-four-case-checkpoint/`. The final runner hardens baseline selection by choosing `baseline-compute_qualification.cpp`, irrespective of candidate source state. Running its `baseline` option now would run all five final cases; that full five-case baseline invocation was not executed and must not be claimed as our evidence. Individual outcomes and signatures are in the three run manifests and logs.

For a normal repository test build, apply `patch.diff` to the exact base in a separate checkout and use the existing test_btx target, selecting the five names below in `compute_profile_tests`. This is the proposed native integration path, not an entry point executed in this investigation:

- `toy_qualification_solves_verifies_and_rejects_replay`
- `qualification_rejects_bounds_expiry_and_corrupt_registry`
- `qualification_quarantines_non_object_rows_and_recovers_empty`
- `qualification_quarantine_failure_preserves_source_and_reports_error`
- `qualification_quarantines_invalid_field_types_and_schema_overflow`

Expected candidate behavior: valid toy CPU work/redeemed persistence remain correct; the first process/instance loading corrupt registry data remains unhealthy and fails closed, exact bytes move to quarantine, and a new instance starts empty with old issued/redeemed challenges unknown and unredeemable. A nonempty quarantine-directory collision leaves source bytes/marker intact, reports an actual failure and exposes no completed-quarantine path; removing the fixture obstruction restores ordinary isolation/new-instance recovery.

Native Windows/MSVC remains unverified. Reuse the existing reported Windows case unchanged to qualify that platform's stream-lifetime behavior. Mac malformed-JSON passing on both variants is preservation evidence only. New registry instance construction is not daemon restart; no live node, mining/device-admission qualification, wallet, GPU or VM ran.
