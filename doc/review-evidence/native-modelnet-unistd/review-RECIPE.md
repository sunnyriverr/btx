# Native Modelnet direct-header repair — dispatch recipe review

**Verdict: PASS for the scoped native component comparison, subject to final artifact verification. No build or test was executed by this reviewer.**

Reviewed `repair/runner.py`, `workflow.yml`, `payload.json`, `closure.json` and product files. Runner SHA-256 at review: `a3f9805899cd36467545c6f636ebfb4770bd7b9fc93ea2f3cfa72916ce248a36`; workflow: `89c2038e90b69b99ceb638210f5aaca1d6ae0a24c8b90fda23822974040d667e`. Only this reserved review file was written.

## Inputs and target scope

All 46 payload source/header blobs were checked byte-for-byte against immutable `2cdff4fc38571df6996d88018bf0ce4d0077b755` and their recorded hashes. All three product blobs match their prepared files and manifest hashes. Both extracted Windows CMake blocks match the closure record; the standalone test bytes are identical between baseline and candidate.

The object target compiles the actual selected package_execute.cpp and capability_control.cpp, using their real closure. No implementation stubs or altered production files are used. The bounded CMake project deliberately substitutes only the project envelope, includes, C++20/static-CRT settings and known Windows definitions; it is not the stock root project and has no OpenSSL configure/link requirement. This difference must remain visible in the result.

The candidate adds the native directory only inside WIN32/MSVC and PRIVATE to the production target. The test explicitly imports that target's include/options/definitions as a standalone route control, not as an assertion that these PRIVATE settings propagate to test_btx. Existing forced include and link libraries remain.

## Failure propagation and records

- Two compilers and two variants are fixed loops. Configure failure records an error and continues; candidate object/control failure records an error. Runtime failure, missing expected success output and absent include trace record errors. Exceptions, including subprocess timeouts, are captured as errors. Result JSON is written in finally, and the final exit is nonzero if errors exist.
- Baseline requires a failing production target and standalone build, with unistd.h present in each aggregate log. This proves aggregate target failure; claims about each production seed's precise diagnostic must be checked against the actual logs before handoff.
- cl `/Bv` may return nonzero without an input; that query is version evidence, not a compile/test verdict. Named configure/build/runtime exits determine the outcome.
- The workflow uses a native Windows runner, x64 VS environment, pinned checkout/upload actions, read-only repository permission, cleared CL/_CL_ overrides and an eight-minute job bound. Upload uses always() so failure evidence is retained.
- Source hashes, actual compile commands, generated CMake envelope, logs/exit codes, include dependencies, executable hashes/copies and object hashes are recorded. Final collection must verify all four variants and named production objects rather than infer them from a green workflow alone.

## Tightening suggested before dispatch

The dependency check currently searches generic `compat` and `unistd.h` text. Prefer normalizing path separators and requiring the exact `src/compat/msvc/unistd.h` route, with both production object hashes present. The standalone guard also proves that route; this strengthening makes the saved evidence less ambiguous. A change only to these assertions does not alter product semantics or require a new design investigation.

## Claims permitted after success

The result can establish baseline direct-header compile failure, candidate compilation of two representative production objects and ten direct-header runtime checks under the named native compilers. MinGW/Unix CMake route evaluations are source/CMake controls unless those platform compilers are actually run.

It cannot establish stock root configuration, complete Modelnet linkage, helper startup, full native node/test_btx execution, all remaining header/caller compatibility or release qualification. If compilation advances to an unrelated existing error, classify it rather than broadening or weakening the repair silently. OpenSSL, remaining unit environment/Metal/OPAQUE boundaries and compiler arithmetic remain separate.

## Final dispatch verdict

PASS. Runner `047e8567e051f3f05aa6343e1957515c6976c540fe89532834979642a13719f9` implements the suggested exact normalized native-header dependency path and requires hashes for both production seeds. Product/payload and workflow scope remain unchanged. Parent will inspect individual baseline seed diagnostics before claiming each fails at unistd. No further design or recipe review is needed absent a material change; final execution/artifact verification remains the next gate.
