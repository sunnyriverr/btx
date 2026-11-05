# Model-search CLI conversion — tested repair

Fix 28f85e6db0f607635aa3c64c3567826249ab1603 on accepted666673a3153225ba264c7870e0e82e354df86765. Changes 3conversion-table entries and adds one maintained rpc_tests case. Existing json_object conversion accepts query objects and preserves literal text for searchmodels/searchpublishers/searchcollections. Attribution: repch1c’s RPC-help failure report led to this independently classified finding; the existing object-conversion implementation is reused unchanged.

## Actual execution

[Native component run 42098634455](https://github.com/sunnyriverr/btx/actions/runs/42098634455) executed fixture 16d85af1b226523e3cf40374fae5627735fcd825 on Ubuntu 24.04 x86_64/GCC 13.3. Its [workflow](https://github.com/sunnyriverr/btx/blob/16d85af1b226523e3cf40374fae5627735fcd825/.github/workflows/model-search-text-object.yml) explicitly fetches baseline 666 and installs libboost-test-dev. The executed command was `python3 contrib/devtools/model-search-text-object/run.py` in that fixture checkout. That exact runner is retained here as run.py, together with workflow.yml. To repeat, use that immutable fixture checkout; this evidence branch contains the repair and is not the baseline execution checkout.

The runner extracts the exact new in-tree case body, verifies removal restores the original rpc_tests.cpp, and compiles the same regression object against baseline, candidate and an intentionally incomplete also_string variant. It asserts candidate client bytes equal baseline plus only the 3initializer changes. Baseline exit 201 / 78 failed assertions; candidate exit 0 / 254 passed; incomplete variant exit 201 / 30 failed. The 8 unaffected conversion controls pass in all variants. Full logs/result/source/case/binary hashes are in records; manifest.json hashes each published input and log.

## Controls and limits

Both named and positional inputs cover ordinary/empty text, numeric/boolean/null/array/quoted JSON-looking literal text, malformed JSON-looking text, equals-sign text, omitted input and two query objects. Query object type/content, including numeric limit, remains intact. Existing numeric/string/hostmodel/getmodel/object-only browse controls remain enabled. No pre-existing assertion or rpc_help check is changed.

This qualifies the converter and exact maintained case body in a standalone Boost runner. It does not qualify the full test_btx fixture, full node/helper search, native Mac/Windows, network search results or a release. The broad rpc_help conversion-table mismatches remain; this is not a full-test PASS. No node, helper, wallet, signing or production work ran.

Compatibility: deliberate JSON-encoded string bytes such as `"llama"` now remain literal quoted search text rather than being unwrapped. Ordinary shell quoting is removed before conversion and is unaffected. Non-object input follows the existing object-or-literal-text converter contract.

Two preliminary CI attempts stopped before the regression: 42098350423 lacked the baseline Git object in a shallow checkout ; 42098510682 lacked Boost headers. The final recipe fixes both prerequisites; candidate and case bytes did not change. Full code diff remains the clean 2-file commit; no prerequisite patches or test relaxations were added.
