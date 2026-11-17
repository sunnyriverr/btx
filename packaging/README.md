# Patched packaging helper — source preparation only

This helper preserves the existing package-only API:
package(w, inputs, python, run, records, tick=...) returns a dictionary.
It has not been executed, imported, syntax checked or tested during preparation.

The original compiled input remains artifact14313303910/source074. All17 compiled input digests,3368-object controller admission, separate source88 Atlas identity and all18 wrapper/real-component plus guard checks remain required. No C++/Rust/configuration call or altered input binary is introduced. The parent controller retains restore, source/dependency/profile checks, capacity/deadlines/process cancellation and original compiled checkpoint retention.

## Explicit packaging implementation delta

The helper requires inputs.packaging_patch to contain the five pinned values:
base_source074dac167c26c1e091198f691ed5727817dba88a; relative_path scripts/release/bundle_python_runtime.py; original SHA256018d8dcbb0bfec2c36e62397b80dcad884b67422e0328409d189ba6cfb5aa2d4; candidate721fa1f54b51223cde80a1c85c4b8c996da916c5dab2fd7ff4fc17a8be72eab7; patch9ad1291bf4924465066c0f9ad11d06d823feaa6147a1f08a6c26859bc4795140.
The scope string is exactly:
Packaging implementation only; compiled product source and original object/binary bytes unchanged

Portable comparison and independent evidence review SHA256 values are provenance references from the parent inputs, not checks rerun by this helper. Both exact patch and candidate module must exist under control/patch.

After the current host/Atlas/binary prerequisites pass, the helper inventories the entire original product/scripts/release directory, rejecting source symlinks and nonregular entries, with128-file/four-MiB bounds. It copies that closure, including adjacent support_files.txt, to fresh package-overlay/scripts/release and replaces only bundle_python_runtime.py with the pinned candidate. All other file bytes/modes must match. Python output caches are excluded from the source-file map.

The unchanged source074 packager runs from that overlay with --source-root pointing to the unchanged original product. The final standalone verifier still runs from original product. No all-ELF, ABI, staged-import, dependency, guard, component or environment gate is weakened. The original product Git/source contents remain pristine and protected by controller retention checks; the overlay lies outside compiled checkpoint roots.

Source and overlay implementation maps plus exact diagnostic source hash are recorded before use and verified after the diagnostic/packager call even on a controlled failure. A deadline can interrupt this verification; such a result cannot be admitted. The original controller's compiled-object/source integrity checks remain separate. A compiled checkpoint does not include this overlay or imply that the Python patch has been applied to its product source.

## Actual interpreter-selection evidence before packaging

record-python-selection.py is a separate bounded diagnostic, not a shipping verdict. It accepts only the recorded isolated workspace and selected toolcache Python3.12.16. It loads the exact original/candidate modules, obtains the maintained SwapNet import list and calls the maintained isolated interpreter probe exactly once. Both pure selectors receive that same actual module map.

The diagnostic retains module paths, prefix/stdlib layout, required imports and both selected-root maps in build-records/python-selection.json. It requires host imports to succeed and the actual cryptography module to be in direct nested site-packages, omitted by the original selector and selected at the expected root by the candidate. Failure is separately labelled package-python-selection / SELECTION_DIAGNOSTIC_FAILED, never a package/shipping failure or a pass. The surrounding controller's native-execution disclosure must distinguish this host-Python probe from BTX version checks.

This60-second probe shares the existing900-second overall package/probe budget. It does not compile or run BTX, but it does execute the selected host Python and imports; future execution authority is required. The current packager subsequently performs the disclosed input btxd-version and staged/bundled Python native probes. Standalone --no-launch does not cancel those earlier probes.

## Evidence and limits

On full successful package/component/final-verifier admission, output sidecars retain:
- package-implementation.json and python-selection.json;
- packaging-evidence/nested-site-packages.patch;
- packaging-evidence/bundle_python_runtime.py;
- packaging-evidence/record-python-selection.py;
- packaging-evidence/manifest.json binding exact retained bytes.

These live outside the shipping tar and do not change its contents or gates. Original compiled and old Atlas producer attribution remains separate from candidate packaging implementation provenance. The candidate cannot rely only on a shorter-lived log artifact or mutable branch to explain the patch/diagnostic. On failure, the records artifact retains implementation/selection evidence and the original controller attempts compiled checkpoint retention; no candidate is admitted.

A helper success remains PACKAGE_STATIC_GATES_PASS_RUNTIME_QUALIFICATION_PENDING. It does not prove GUI, installed-tree, wallet/daemon service, restart or official adoption. This preparation performs no script/native probe/test/build/CI/publication, no wallet or key access and no automatic retry.
