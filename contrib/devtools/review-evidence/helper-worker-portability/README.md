# #338 item18: combined descriptor cleanup + Windows guard

**Use combined code commit 0f94479c71275e5b61f20a66ee38a74487afcaf9; it supersedes the earlier unguarded
b9e1a19c candidate.** This branch includes both commits. Cherry-pick both code
commits in order, or apply guard/combined.patch once to cbf65894. Do not apply the
combined patch on top of those same commits. Evidence is a separate commit.
Original report: repch1c. Candidate and scoped tests: Sunny River, AI-assisted.
Original subprocess utility authorship unchanged. Earlier Mac runtime evidence is
[historical here](https://github.com/sunnyriverr/btx/tree/6d74e40277c977a981c109c36783f618c27670e5/contrib/devtools/review-evidence/helper-worker-fix).

## Correction and results

The first candidate referenced a utility excluded on MinGW/MSVC. This correction
guards that POSIX include and uses a private forwarding wrapper: same cleanup in
all four POSIX worker children; no excluded Windows API reference. Windows' existing
fork shim still returns ENOSYS. It does not add Windows CUDA/generation spawning.

| Scope | Evidence |
|---|---|
| Linux baseline resident-worker restart | FAIL3/3, worker alive, replacement cannot bindTCP |
| Linux combined correction | PASS3/3, worker alive, replacement bindsTCP |
| Idle and unload restart | pass on baseline and corrected helper |
| Inference, generation stdin/JSON, llama argv/stdout, exit-error recovery | pass on baseline and corrected helper |
| Mac combined correction | full helper TU syntax and native extra-descriptor/stdIO cleanup pass |
| MinGW/MSVC-target API boundary | missing-declaration failure before, compile success after |

Linux is actual full CMake helper target on Alpine3.22.4/aarch64/musl, GCC14.2,
OpenSSL3.5.9, UID501; Release configuration with explicit-O1, no GPU/wallet/node.
Both variants share a necessary pre-existing build prerequisite: adding cstdint
in swarm_membership.h. That include is not part of this descriptor patch and is
recorded in the build notes. Actual guard-revision helper SHA256:
`c4d3991027719f24f4b01099014719ed42b888938bfd2fa625c8814047bd3943`.
The baseline/helper-source identities are in linux-original/runtime-summary.json.
The original five-line candidate and the combined correction were both tested;
only final/proc-checked runs are counted in the table.

**Windows limits:** target-boundary probes compile the exact guarded declaration
excerpt and actual wrapper to COFF. They are not full-header/helper-TU, SDK, link,
native Windows or release qualification. Mac guard validation is syntax/native
cleanup, not a new Mac full-helper relink/restart matrix. Synthetic model/adapter
fixtures only; no real CUDA/inference, production chain, full suite, PQ1 transfer
or default release qualification.

## Reproduce the Linux runtime comparison

On a disposable native Linux host with CMake/Ninja, C++20, Boost and OpenSSL3.5+,
build btx-modeld from cbf65894 and the combined code revision separately. Apply the
same one-line cstdint prerequisite to both trees. Exact configuration/flags are in
linux-original/CMakeCache.txt, full-configure.log and bitcoin-build-config.h. Stored
paths are sanitized and must be replaced with your own source/build directories.
Do not reuse a production catalog or datadir. The fixture only uses loopback and
explicit owner-configured native adapters; no real model or GPU is required.

Build the two tiny fixtures from this directory:

    cc -std=c11 -D_DEFAULT_SOURCE -O1 -Wall -Wextra -Werror helper-worker-inheritance/adapter.c -o helper-worker-inheritance/adapter
    cc -std=c11 -D_DEFAULT_SOURCE -O1 -Wall -Wextra -Werror helper-worker-fix/control.c -o helper-worker-fix/control

    python3 helper-worker-fix/reproduce-proc.py --binary /absolute/original/btx-modeld --out /absolute/new-before --cases resident-crash,resident-crash,resident-crash,idle-crash,unload-crash
    python3 helper-worker-fix/reproduce-proc.py --binary /absolute/corrected/btx-modeld --out /absolute/new-after --cases resident-crash,resident-crash,resident-crash,idle-crash,unload-crash
    python3 helper-worker-fix/controls.py --binary /absolute/original/btx-modeld --out /absolute/new-controls-before
    python3 helper-worker-fix/controls.py --binary /absolute/corrected/btx-modeld --out /absolute/new-controls-after

Require standard lsof4.99+, not BusyBox's applet; this version uses /usr/bin/lsof
and Linux /proc for child-liveness assertions. Baseline regression must exit1 and
corrected must exit0. Raw pass marks completed scenario/cleanup; regression_pass
also requires descriptor closure. Baseline unload's stronger closure predicate
fails before unload, although unload/restart succeeds. Adapters are finite and
report zero GPU bytes/smoke_passed=false; helper fields do not prove CUDA admission.

## Reproduce focused Windows compile check

The four windows-boundary/*.cpp inputs are the exact exercised probe sources.
Use Clang with --target=x86_64-w64-windows-gnu or --target=x86_64-pc-windows-msvc,
-std=c++20 -Wall -Wextra -Werror -c. Each *before.cpp must fail for the missing
subprocess_close_all_fds member; each *after.cpp must compile. No runtime/SDK
claim follows from that narrow check.

## Required independent acceptance

Run a full supported MinGW Windows CMake helper build, link and startup/local-RPC
smoke. Check configured worker requests still fail closed as expected from the
existing unsupported-fork shim; successful Windows worker spawning is not promised.
Native Windows execution is still outstanding. No Numair decision or new PR is
requested by this evidence update.

## Pilots and limits retained

The first1GiB VM build ran out of compiler memory; temporary3GiB compiled helper.cpp
but host swap triggered a storage stop. Build resumed at1.5GiB, finished and VM was
stopped/restored1GiB after tests. An extracted-function pilot was compiled but not
counted. Initial missing header closure was corrected before any component run.
Full CMake's independent missing-cstdint failure was fixed equally for both variants.
First runtime used incompatible BusyBox lsof and is excluded; standard lsof then
worked. BusyBox ps left liveness blank in early runs; final restart runs use explicit
/proc non-zombie state. No product change was made to satisfy those measurements.
Guarded revision reused the same cache/settings and ran the hardened harness.
Full Linux guard results and short rebuild log are under linux-guard/. All files
are source/config/log/JSON evidence; binaries and private identities are excluded.
