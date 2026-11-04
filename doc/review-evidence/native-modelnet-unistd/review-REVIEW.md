# Current native Windows prerequisite review

**Verdict: #396 removes its measured native header/storage barriers; a stock full native build remains blocked. A native-only forwarding header is a coherent next inclusion-boundary candidate, provided it exposes only the already accepted adapter and preserves unsupported-operation failures.**

Source-only review on `2cdff4fc38571df6996d88018bf0ce4d0077b755`, 4 November 2026. No compiler, test, runtime, VM, network mutation, Git mutation or delegation occurred. Only this reserved report was written. This does not assert a new native compiler diagnostic or verify peer executions.

## Accepted delta

The complete `ab1b5cbe..2cdff4fc` list is five paths: `src/compat/mingw/posix_extra.h`, `src/modelnet/CMakeLists.txt`, `src/modelnet/erasure_store.cpp`, and two standalone tests under `test/util/`. No other production or unit source changed.

The native branch of the forced header now avoids its own `unistd.h` include and supplies `ssize_t` (lines 111–117). Modelnet now selects `/FI` on MSVC-compatible compilers (CMake lines 2571–2576). Erasure storage has the accepted native-header and binary-output correction. These existing scoped results do not qualify the full node.

## Remaining dependency profile

- `windows-clangcl-static` still sets `BUILD_TESTS=OFF`; acceptance must override this to ON and retain default Modelnet ON.
- `vcpkg.json` still lacks OpenSSL. Its pinned baseline resolves to 3.3.2#1 in the prior exact-baseline audit, while `src/CMakeLists.txt:1905–1911` requires 3.5+. A separately provisioned compatible prefix can preserve source, but actual architecture, CRT, static linkage, version and CMake resolution need recording. Merely adding OpenSSL at the old baseline is insufficient.
- Root CMake lines 442–448 select static CRT for the static triplet; 465–478 look for clang's Windows builtins library. Plain cl's recorded arithmetic limitation remains separate. Do not change arithmetic or tolerate duplicate symbols to pass this gate.

## Direct native header boundary

Root CMake lines 439–440 and Modelnet CMake lines 2567–2570 add the compatibility include directory. It supplies socket/poll/wait adapters but no `unistd.h`. Avoiding the forced header's own include does not satisfy later direct includes.

| Selected production source | Direct include | Modelnet CMake line |
| --- | --- | --- |
| `capability_control.cpp` | `unistd.h:21` | 2535 |
| `package_execute.cpp` | `unistd.h:18` | 2500 |
| `source_registry.cpp` | `unistd.h:28` | 2516 |
| `helper.cpp` | `unistd.h:90,109` | 2422 |
| `generate.cpp` | `unistd.h:22` | 2421 |

These sources remain byte-identical to `ab1b5cbe`. Original #356 already identified this error class; do not rerun a whole build merely to rediscover it.

A separate include directory enabled only for MSVC-compatible compilers, with `unistd.h` forwarding to the accepted `posix_extra.h`, is a plausible narrow fix. Its guard prevents recursion, and the `_MSC_VER` branch already skips a system unistd include. This avoids shadowing real MinGW/POSIX headers and requires no `include_next` trick. It must add no dummy-success APIs and preserve current `ENOSYS` process refusals. It does not implement Windows helper spawning.

Keep the initial scope aligned with `bitcoin_modelnet`, which already force-includes that adapter. Moving the include path to `core_interface` also exposes the adapter's process/socket macro rewrites to core/test translation units that include unistd; that wider change requires explicit compile/include-order controls. Native representative direct-include production compilation plus existing environment/binary-I/O/unsupported-process controls can prove progress without claiming a full build.

## Remaining unit boundary

- `src/test/CMakeLists.txt:91` unconditionally selects `matmul_backend_capabilities_tests.cpp`, which includes unistd at 24 and calls setenv/unsetenv at 47–58.
- Its Metal zero-copy case has a runtime availability return at 1091–1093, but still compiles sysconf at 1101 and posix_memalign at 1107. Runtime unavailability is not a Windows compile guard. Preserve that test on its supported platform rather than adding fake APIs.
- Modelnet ON selects `modelnet_035_disk_tests.cpp` at test CMake line 607, with setenv/unsetenv calls at 50/52. The library's forced include is PRIVATE; no root/test-target forced option supplies the wrappers to these unit call sites. Wrappers exist at `posix_extra.h:292–300`; their component correctness does not establish call-site availability.
- `test/util/shielded_v2_egress_fixture.h:202,218` and `test/shielded_v2_bundle_tests.cpp:176` still use `ScanDomain::OPAQUE`. The SDK macro collision is unchanged; `compat/compat.h` has no cleanup. Trace actual native include order before choosing a cleanup site. Do not rename the protocol enum for a unit compile boundary.

These are known #356 items 5/6. A unit-only environment/Metal portability repair is finite and useful, but cannot alone unblock the full default-ON node. OPAQUE remains another separate prerequisite. Pruned test lists, Modelnet OFF and local shims do not qualify stock acceptance.

## Decision and evidence limits

The direct-header repair has higher immediate leverage than a fresh isolated test-macro fix because it addresses selected production sources using an already accepted adapter. Prove representative native compilation and preserved adapter behavior before broadening its target scope. The OpenSSL setup is still required before root-generated compilation can establish actual project flags.

The following sampled files were checked byte-identical from ab1 to 2cd: root CMake, CMakePresets, vcpkg manifest, src CMake, test CMake, capability_control, package_execute, source_registry, helper, matmul_backend_capabilities_tests, modelnet_035_disk_tests, compat/compat.h and shielded_v2_egress_fixture.h. No new platform qualification is inferred.

Parent owns current public ownership/CI assessment in `ownership.json`, final task selection and ledger/publication. This review does not exclude private work or justify a post restating known blockers.
