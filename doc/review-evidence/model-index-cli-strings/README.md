# Model-index CLI endpoints: literal strings

**Fix `af35ac11`: documented positional and named add/remove commands work without JSON-encoding the endpoint.** Code commit `af35ac119cc9b01a9cc493801b1fd83111a9b6c8`, parent accepted `666673a3153225ba264c7870e0e82e354df86765`.

Only two conversion-table rows are removed from `src/rpc/client.cpp`. Both methods declare STR; the existing no-conversion path preserves literal endpoint/identity bytes. The new maintained case is `rpc_tests/rpc_convert_modelindex_endpoints_are_strings` in `src/test/rpc_tests.cpp`. No helper, node or general parser code changes.

## Exact before/after

| Native check | Baseline | Candidate |
|---|---|---|
| Same new in-tree regression body in component runner | 64 failures / 98 assertions; exit 201 | 138/138 pass; exit 0 |
| Same actual CLI workflow success oracle | Four required properties fail; exit 1 | All four pass; exit 0 |
| Incomplete also_string-only change, same unit body | 24 failures / 118 assertions; exit 201 | Deliberately rejected control |

The C++ test uses 11 literal inputs, both methods and positional/named forms. It always asserts string type and checks exact bytes only after a passing type guard; differing assertion totals on failed variants avoid secondary `get_str` exceptions. Inputs cover ordinary IPv4/IPv6/hostname endpoints and JSON-looking literal identities, including quoted/empty text. Six additional assertions preserve unrelated object/union conversions. Assertion counts are not distinct test counts.

The identical `paired_workflow.py` file and the same four success expectations are used for both executables: ordinary positional/named add and remove must exit 0, enter the adapter once and produce the exact expected peer list. Baseline arguments fail JSON conversion before HTTP. After recording a failed add requirement, direct RPC establishes the target so baseline removal is not vacuous. Candidate requests succeed with an unrelated sentinel preserved. Both phases finish direct-request controls and cleanup. Baseline has 38 passing safety/valid guards; candidate has 34, because the same code records error diagnostics on failure and response invariants on success. No expected-outcome mode changes the four required properties.

## Executed profile and recipe

Native Alpine 3.22/aarch64/musl, GCC 14.2, retained O1/C++20 profile with its existing `-include cstdint` prerequisite. The baseline CLI was manually built from four unchanged accepted-source translation units, then the candidate was partially relinked with only its new converter object. This is not a stock maintained-target build. `baseline-build.json`, `native-preflight.json` and `result.json` record source/object/archive/executable identities and exact commands. Seventeen retained baseline files, eight dynamic libraries and one generated header were checked before the run. All 14 original archives, baseline CLI/converter object and helper bytes remain unchanged.

The real helper is source `5eb69ade` (accepted base plus pending #413), SHA-256 `3cb44a7d3118e11e858633c9cba622bbbb73899ba5a711b762fd2f9b29a63123`. Its index handlers are unchanged; this repair does not depend on #413. The baseline CLI is `a4402a03c140bec25e0d60d24a9f6359db9c3d1038d78c9474ac64761b21969f`; candidate is `bc74ac1248e9cbee5729e30748b874dd7af5fd6b4ab6d05cbd439643c6751c3c`. Hashes were checked before and after execution.

`run_guest.py` is the executed retained-cache phase driver. It compiles the exact maintained test body, links baseline/candidate/partial-control runners, partially relinks the CLI and invokes `paired_workflow.py` twice with executable path/hash and output-file arguments. The latter are artifact parameters, not alternative acceptance expectations. Those scripts depend on the recorded task workspace/cache; they are not a portable one-command build wrapper.

For a normal maintained unit build, the intended entry point is:

```
build/bin/test_btx --run_test=rpc_tests/rpc_convert_modelindex_endpoints_are_strings
```

That full-fixture entry point was not executed here; the component adapter ran the exact case body without `RPCTestingSetup`.

## Compatibility and limits

The former workaround of adding literal JSON string quotes becomes literal endpoint text on the candidate. After applying the fix, use ordinary shell quoting, e.g. `btx-cli addmodelindex '127.0.0.1:37491'`. Programmatic JSON-RPC string requests are unchanged. This is a CLI representation correction, not a changed helper endpoint policy.

Actual CLI processes used a numeric-loopback HTTP fixture forwarding successful results and unchanged endpoint bytes to the real helper's Unix RPC. The fixture normalizes the sole named endpoint object into an array; production node RPC registration, permissions, named binding and error serialization are not qualified. Helper errors would raise/disconnect in the fixture rather than demonstrate JSON-RPC error parity. `addrman=false` and spend=0 are helper response invariants, not observations of a monetary node.

No full `test_btx`, node, external transfer, endpoint reachability, restart persistence, Mac/Windows, concurrency stress or release qualification. Helper discovery, hosting and following were disabled; its observed TCP/UDP socket sets were empty. Preferences/runtime/cookies were removed, helper exits were 0 after SIGTERM with no kill fallback, adapters closed and the VM stopped. No wallets or production resources were used.

A source-only merge-tree check against #419 (`28f85e6d`) is clean; no combined runtime run is claimed. Existing source authorship is retained. Sunny River authored this repair; repch1c's RPC-help audit prompted the investigation and is acknowledged in the code commit. No external review/adoption is inferred.

Logs have only ANSI color escapes removed; `source-map.json` records original/public hashes. `manifest.json` covers published files. Nothing was retested for publication.
