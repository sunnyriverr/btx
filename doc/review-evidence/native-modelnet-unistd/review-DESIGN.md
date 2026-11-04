# Native Modelnet direct-header repair — design review

**Source-design verdict: PASS for the scoped inclusion repair. Dispatch recipe has not yet been reviewed; it was not present at this inspection.**

Reviewed immutable accepted base `2cdff4fc38571df6996d88018bf0ce4d0077b755`, `repair/prepare.py`, `repair/closure.json`, and the three files under `repair/product/`. No build/test/runtime/network/Git mutation was performed. Only this reserved review output was written.

## Scope and safety

- The only production CMake delta adds `compat/msvc` as a BEFORE PRIVATE include directory inside the existing WIN32 and MSVC branches of `bitcoin_modelnet`. It does not export the directory through core_interface or to unit/third-party targets. MinGW and Unix retain their original routes.
- New `compat/msvc/unistd.h` forwards to the accepted `compat/mingw/posix_extra.h`. Both headers have guards; the accepted adapter's native branch already avoids system unistd. Existing Modelnet `/FI` remains intact, so native Modelnet already sees these adapter definitions and process/socket macros. The forwarding header changes header resolution, not those semantics or their target scope.
- Accepted adapter SHA-256 remains `95b5941be1108017c1f5e4e05ef9615dbbd1f8877c5d5fc1ab3c98da543c4c50`. No new fake-success implementation, process spawning, validation rule, arithmetic, codec or I/O behavior is introduced.
- The standalone source is explicitly not registered as test_btx. It must not be presented as an in-tree unit-suite result.

## Acceptance controls

The direct-header test intentionally includes unistd and verifies the forwarding header guard plus `_MSC_VER`. It has ten checks: isolated environment name, set, refusal to overwrite, permitted overwrite, environment cleanup, pipe availability, write count, exact binary bytes, descriptor cleanup and fork refusing with ENOSYS. Its six-byte payload exercises NUL, LF, CR, control-Z and high bytes. The pipe is small and synchronous, with no external helper or network operation.

The generated per-process environment name is checked absent before mutation and removed on the passing path. If a broken adapter reports success without creating it, construction of a string from a null getenv may terminate rather than report the named check; this still fails the test and does not permit a false pass, but diagnostics could be clearer. It is not a product-source correctness blocker.

The two unchanged production seeds, package_execute.cpp and capability_control.cpp, are actually selected by the accepted Modelnet target and include unistd directly. The closure uses real project headers, not mocked implementations. Compiling them is a useful inclusion-boundary control; it is not linked Modelnet, helper startup, full root-generated configuration or node/unit acceptance.

## Required native recipe checks

Before dispatch, verify that the runner:

1. Uses the exact recorded baseline/candidate Windows CMake blocks, the same standalone test bytes and the same production closure in both variants, with all source hashes checked.
2. Exercises both native cl and clang-cl under the selected static CRT and C++20 flags; records actual commands, flags/include order, SDK/compiler versions, object/executable hashes, output logs and exit codes.
3. Preserves applicable core Windows definitions, including NOMINMAX and the target SDK floor, in the bounded component project. Otherwise an incidental macro failure must be classified as a harness mismatch rather than a product regression.
4. Confirms baseline failure is the direct unistd route and candidate success genuinely resolves the new native header. Existing `/FI` alone is not enough to prove that header route; the standalone sentinel helps distinguish it.
5. Does not turn another existing production-source error into permission to modify unrelated source or silently relax flags. If a seed advances past unistd and fails later, record that next barrier and narrow the claim.
6. Retains MinGW/Unix route preservation as a source/platform-control result unless those compilers are actually executed. No native full-root, complete library, helper, Windows test_btx or release claim follows from these components.

The root OpenSSL/profile and remaining test portability prerequisites remain open. This narrow repair has useful leverage, but does not close #356. Parent owns final recipe review, execution, ledger and any authorized delivery.
