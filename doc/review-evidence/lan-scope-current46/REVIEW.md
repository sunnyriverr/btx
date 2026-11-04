# Current LAN integration and coverage review

Reviewed 4 November 2026 by the bounded `lan_current_review` child of BTX session 2; updated after inspecting the owner's qualification artifacts. This child performed no build, network/runtime test, VM operation, Git mutation, public action or shared-ledger write. The only written output is this report.

Verdict: no concrete current-base integration defect found in the three product-file changes or the supplied qualification artifacts. The current Linux production-object compile and legitimate discovery-to-hint checks close the two narrow integration gaps identified in the initial review. Scope remains component/object qualification, not a full helper build or native Windows qualification. Historical receive-boundary experiments need not be repeated.

## Exact inputs and preservation

Compared `source/src/modelnet/native_discovery.cpp`, `.h` and `source/src/compat/mingw/posix_extra.h` with the corresponding `evidence/accepted/` copies. `integration.json` identifies accepted base `46caec762b0f130d497313d8ca9fa6894ac19ccd` and historical product-only candidate `af1ffda2a5394061a98a3c50fc639b6dd8299875`. Independently recomputed candidate SHA256 values match all three entries in that receipt:

| File | SHA256 |
| --- | --- |
| native_discovery.cpp | d6265aea738a1f3d86047e96417fa47fba5c40561b228e356261374fbd1eb9af |
| native_discovery.h | 6e8815154f3ea113366ddbab7110913201dc71e9e8cd050512a45813ba31f1f5 |
| posix_extra.h | ddc3ad091ded24d26e5e2c2af4db1c75c494ad101e64a111b7901c3f5ecc0355 |

The accepted `ValidPort(uint16_t)` function is byte-identical, including `IsForbiddenControlPort`, the discovery-port exclusion and the explicit 29442–29446 exclusions (`native_discovery.cpp:47–55`). Encoding, decoding and hint-book admission still use that function through `EncodeLanBeacon`. There is no replacement of the accepted control-port policy by the historical candidate's older policy.

Removing the single added early `#include <mswsock.h>` from the candidate Windows shim produces the accepted shim byte-for-byte. The native CRT `_MSC_VER`/`ssize_t` handling, MinGW handling, FAR/NEAR compatibility definitions and all other accepted declarations are retained. The early include precedes the shim's `VOID`/`CALLBACK` removal; the later discovery-TU include therefore does not first parse that SDK header after those macros have been removed. The historical `combined-header-result.json` demonstrates this ordering issue only for its recorded MinGW header slice; it is not a current full-TU or native Windows pass.

## Build and caller boundaries

`src/modelnet/CMakeLists.txt:23` includes the actual production discovery TU. On Windows the library receives the current forced compatibility header through `/FI` for MSVC or `-include` otherwise (`:2568–2581`); existing links include `ws2_32` and `iphlpapi`. The patch obtains the receive function through `WSAIoctl`, rather than introducing a direct `WSARecvMsg` link call. Root CMake sets `_WIN32_WINNT=0x0A00` (`CMakeLists.txt:434`). These source/build observations establish the intended compile boundary, not successful compilation against a native SDK.

Apple-only `sockaddr_dl` is guarded together with `<net/if_dl.h>`; Linux receives through `IP_PKTINFO`/`recvmsg`; Windows uses `IN_PKTINFO` and the Winsock message API. Unsupported OS branches refuse receive-scope setup. There is no fallback that silently accepts a packet without interface/destination metadata. Membership changes from address-based `IP_ADD_MEMBERSHIP` to interface-index `MCAST_JOIN_GROUP`, so an actual current component build matters even where the older implementation compiled.

The supported helper caller remains `helper.cpp:12140`: LAN discovery is opened only with configured LAN discovery, a TCP listener and a parsed listen address. Open failure remains logged and disables discovery. `Tick` is called from the existing helper loop (`:12399`) and endpoints feed the existing candidate path (`:5246`). This review did not exercise automatic connections.

## Existing coverage and actual gaps

`src/test/native_discovery_tests.cpp` is already included in the maintained test target (`src/test/CMakeLists.txt:609`). Its nine cases cover canonical wire/network handling, source/port policy, all-chain RPC/P2P port exclusions, hint expiry/bounds and neighboring acquisition/identity rules. None instantiates `NativeLanDiscovery` or calls `Open`/`Tick`; none exercises ancillary metadata, selected-interface membership or receive-path legitimate progress. Passing those tests alone cannot qualify this receive-interface patch.

Historical `lan-portability/COMBINED-REPORT.txt` covers the exact historical LAN body on macOS, focused synthetic policy cases and the Windows header-order slice. Historical `lan-linux-native/REPORT.md` adds an actual Alpine/musl CMake helper build and legitimate multicast discovery, with its precise shared-prerequisite and incremental-build limitations. Its Linux result supersedes the older combined report's then-missing Linux evidence. Neither report is current accepted-46 integration evidence. Those reports already supply the bounded historical receive-boundary/regression observations; a new commit hash is not a reason to repeat them.

## Final qualification artifact review

Inspected `linux_build.py`, `linux-configure.log`, `linux-affected-objects.log`, `linux-control-build.log`, `linux-controls.log`, `controls.cpp`, `mac-object.json`, `mac-object.log`, the retained stricter Mac pilot log, and both Windows prelude fixtures/logs plus `windows-prelude.json`.

| Evidence | Supported conclusion | Material boundary |
| --- | --- | --- |
| Linux root CMake configure, Modelnet ON/tests ON; verbose build of four named objects | Actual generated project compiles pass for `native_discovery.cpp`, `model_nat.cpp`, `helper.cpp`, and maintained `native_discovery_tests.cpp` | No Modelnet archive/helper link, `test_btx` link or execution, daemon or complete suite |
| Direct Linux control executable built from real `native_discovery.cpp` and real `model_nat.cpp` with function/data sections and linker garbage collection | Actual codec/filter/hint-book checks pass for 22 enumerated protected ports and two ordinary ports; actual `Open`/`Tick` receives a valid selected-interface multicast beacon and produces the expected hint | Separate component build, not the root-CMake objects relinked into a helper; no stubbed control-port implementation; no automatic connection, TLS or transfer |
| `own_host_unicast_observed=1` | Own-host unicast also produced the expected hint in this run | Deliberately routing-dependent observation: harness prints this result without making failure affect its exit status; do not describe it as a required asserted acceptance gate or physical LAN unicast qualification |
| Mac full discovery-TU compile, `rc=0`, empty final diagnostic log | Actual current discovery TU compiles natively with the recorded direct Clang flags | Not root CMake, helper link or runtime; first stricter pilot failed only on deliberately unused common-header parameters, retained separately; final suppression matches project warning policy |
| Current shim-prelude plus receive declarations, Windows-target Clang and genuine retained MinGW headers | Late-include control fails with `VOID` errors; candidate early include passes syntax and supplies receive-function, packet-info and membership declarations | Not the complete shim/TU, Microsoft SDK, native Windows compile/link/runtime, or a warning-clean result; common MinGW unused-expression warning remains |

The Linux legitimate control calls the real public `NativeLanDiscovery` methods, binds its sender to the selected address, uses ordinary UDP delivery and checks the exact expected endpoint. It does not inject ancillary metadata or replace the interface enumerator. The initial empty nonblocking `Tick` is bounded by an elapsed-time assertion; socket objects are closed by explicit sender cleanup and the discovery destructor. The ordinary-port controls round-trip the codec and use the actual hint book. Protected-port controls call the actual `IsForbiddenControlPort` provider and require encoder/hint rejection. No new off-scope packet, vulnerability reproduction or automatic-dial campaign appears in these artifacts.

The maintained nine test cases were **compiled, not executed**. The direct executable is focused supplemental coverage and must not be relabelled as a `test_btx` run. This is an explicit qualification limit, not a reason to build the entire unrelated test suite. No essential legitimate current integration control is missing for the stated Linux component/object scope. The final evidence package should preserve exact host/guest source identities and command/outcome receipts; the reviewed logs alone do not independently establish that every copied guest source matches the host worktree.

Native Windows full-TU/component compilation and real receive behavior remain separate unqualified platform gates. Session 1's current `supervisor.h`/`init.cpp` repair does not exercise this LAN TU; do not duplicate that lane or infer LAN acceptance from its results. Current source, peer ownership/status and the parent session's fresh public-overlap check support integration of an existing candidate rather than a new bug hunt. This child did not independently refresh GitHub.

## Closeout

No product change requested by this review; no blocker established for the stated qualification scope. Record the source/command/result identities, cleanup/resource state and these limits in the owner's final receipt, then preserve the no-posting hold. No additional experiment is requested. No runtime, build cache or reservation was created or modified by this child.
