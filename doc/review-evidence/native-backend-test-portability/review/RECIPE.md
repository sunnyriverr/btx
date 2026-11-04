# Candidate and paired recipe — PASS scoped

4 November 2026; independent `/root/windows_root_recipe_review`. Read-only candidate/recipe review; no compiler, runtime, test, API write, source/ledger mutation or delegation. Static Python AST parsing passed. Inputs: PLAN.md, patch.diff, product.json, source-manifest.json, candidate source, runner.py/workflow.yml, corrected component fixture and exact in-tree cases; Mac component assembly inspected.

**Proceed with the bounded paired native object plus helper controls.** No blocking product/recipe defect found. Product4a286b26e68eae661e66eb484d943f7fd31a851b is based on accepted46. Its one-file delta removes unused unistd, selects CRT _putenv_s under _WIN32 and retains both original POSIX branches; two in-tree restoration cases are added. No CMake/production/global shim change or test pruning occurs. Source-manifest baseline/candidate SHA256 values match the reviewed files; extracted in-tree cases exactly match the candidate substring.

The native sequence is discriminating: reconfigure the real supported root with tests ON/default Modelnet ON and existing exact dependencies, query its actual target, and require the known baseline line24 missing-unistd diagnostic. Only then install the approved candidate bytes at the one named tracked path. Compile the same generated target with the identical command; require success and unchanged compile database. Capture the resulting object, not just its producer-reported hash. Whole-source baseline-after and candidate-before/final catalogs retain the explicit expected-working-blob exception for exactly that approved path; every other tracked blob/link remains strict. This exception records a candidate comparison rather than claiming stock source after patching.

The standalone control uses the exact source-extracted helper and exact two added cases, header-only Boost.Test from the provisioned real Boost headers, /MT and C++20. cl and clang-cl each run fresh processes with the test-only variable initially absent and nonempty, independently prepared by Python's child environment. Assertions observe real std::getenv; nested replacement, null removal and absence restoration challenge more than constructor success. This is meaningful component validation of test-fixture behavior, not execution of the full linked test_btx suite or GPU code.

The corrected external global fixture snapshots/checks initial CRT getenv state after all case scopes. It uses plain comparison/fputs/exit90 rather than Boost assertions after framework teardown; this resolves the parent-reported Mac harness pilot. Preserve that pilot as a harness failure. The correction changes no product case or helper behavior. Component source now includes cstdio. Intermediate component objects are hashed before removing only those owned scratch files; the real candidate root object remains retained.

The deliberate no-restore destructor mutant is useful: nested restoration assertions should reject it. Corrected runner now requires nonzero plus a named scoped_environment_restores_ assertion diagnostic containing 'has failed'; unrelated process failure cannot satisfy that guard. A timeout remains SETUP_ERROR. Final artifact review must still inspect the original diagnostics and exit codes, including global-fixture leak reporting.

Planned Mac baseline-helper/new-cases and candidate-helper/new-cases controls preserve the same observable contract. Initially empty POSIX state exercises preservation across outer scopes via the independent global fixture; native runs intentionally do not claim preservation of a distinct present-empty state. Existing Windows CRT empty-removes behavior and the narrow caller contract remain as described in DESIGN.md. No direct empty-value insertion case should be claimed if only initial empty restoration is executed. No MinGW execution is established by using _WIN32, although the accepted neighboring pattern already uses the same CRT API for Windows.

Known limits/stop behavior are appropriate: source/manifest/profile mismatch or unexpected baseline signature is setup failure; substantive candidate compile failure stops with BLOCKED_CANDIDATE_OBJECT and no scope expansion. Full node/helper links, whole test_btx build/run, plain-cl project support and final dependency linkage remain open. Retain ordinary compiler warnings and identify root-object execution separately from header-only component runtime. Existing fork branch/cache reuse does not grant upstream posting authority.

Reviewed SHA256 identities:

- candidate source: `401bcfb060c9a6f05efc56faadb57c3057ab8b46bffc67fb05a626e5ce7fa6f6`
- runner.py: `53c0f238616143118fc4eee4172e45e1d3c3adfd81f82bf8c140c0e68479ab29`
- workflow.yml: `eddc4d74e21d4a366de2c8ca84142a4c5ca4fb41afa0f33bc0904368675e6402`
- source-manifest.json: `33c3dbe73c510f80e4ac37010a85227f2d22f2bdedae9d1c792430cd7a3d36ab`
- corrected component_fixture.inc: `e407eeaa62f9e84e387c8d0ce95d523838b73bd37a1f009358447620508d02b4`
- in-tree-cases.inc: `019c80c4f726d405ae94e041e901647a617fd205800ba4f4e885d38c3b9c20c8`

Remote controls must package candidate.cpp with the candidate hash above and all referenced include/manifest files; the runner's manifest check enforces actual candidate bytes. Parent owns dispatch, final native/POSIX evidence and resource claims; this is recipe review, not an executed pass. Review reservation may be released after integration.
