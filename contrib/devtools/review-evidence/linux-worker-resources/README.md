# #338 item14: Linux native qualification and an inherited memory envelope

**Existing operator mitigation verified through the real native qualification CLI;
no new product fix.** AI-assisted work by Sunny River. Original issue by repch1c;
JPP confirmed the missing Linux cap from code. This branch combines the exact
#337e3d87faf process-guard header and #346a74b8af8 filesystem-jail TU on cbf65894.
Those product changes are repch1c/Jpp-matata work, unchanged and credited here;
only the evidence, bounded probes and build/reproduction drivers are new.

## Workflow and scope

The documented btx-native-qualify tool command reaches Cap02::QualifyNative and
SwarmRunFilesystemJail. Release qualification also uses Cap02 for owner-reviewed
gates; release/signing was source-traced, NOT executed. NativeToolProbe requires
owner-pinned package/executable/output hashes and forbids building that policy
from peer cards. No automatic peer/model-discovery/RPC caller was found.

Linux has CPU/fd/file/wall constraints but no built-in address-space/process cap
in this jail path. Its request exposes no memory-budget field; the platform guide
omits memory from the Linux row. The Mac/Windows adapter chooses8GiB. We therefore
do not claim bypass of a configured Linux budget or a violated8GiBceiling.

## Executed experiment

Actual upstream native_qualification_main.cpp and dependencies linked using the
repository native component recipe: C++20/C11,O1,sectionGC,real ML-DSA objects,
no mocks/adapters. Alpine3.22.4/aarch64/musl, GCC14.2, Linux6.12.81, unprivileged
UID. This is an actual CLI component build, not full-node CMake or release testing.

Pinned static probes request8MiB/96MiB, touch each4KiBpage, check peakRSS>=80%of
the allocation, then write exact expected output. The actual CLI verifies the new
output and rehashes inputs. Allocation failure exits42 before output creation.
The harness applies both soft and hard RLIMIT_AS to the CLI before exec.

| Inherited address-space envelope | Probe | Result |
|---|---:|---|
|128MiB|8MiB|qualifies3/3|
|128MiB|96MiB|qualifies3/3|
|64MiB|8MiB|qualifies3/3|
|64MiB|96MiB|refused3/3: exit2,NATIVE_TOOL_EXIT,no output|

All12finalcases completed in a1GiBVM. Each invocation has a4srequest wall limit,
a6souterCPUlimit and a10scontroller deadline. Maximum requested allocation96MiB;
no OOM or8GiBallocation. Default guest AS limits are unlimited, but every executed
probe was protected by a finite64/128MiBenvelope. No memory-pressure run without
an outer limit was necessary or performed.

## Tested workaround

The existing Linux inherited address-space envelope survives the full tool
qualification path. guest-run.py uses:

    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (cap * 1024**2, cap * 1024**2))
        resource.setrlimit(resource.RLIMIT_CPU, (6, 6))
    subprocess.run([qualifier, 'tool', request_path], preexec_fn=limits, ...)

Apply an appropriate outer limit to an explicitly selected qualification process,
not globally to a production node. The64/128MiBvalues are SYNTHETIC TEST VALUES,
not recommended budgets for real model/tool packages. RLIMIT_AS is virtual address
space, not RSS or an aggregate cgroup budget. A real workflow's envelope must also
allow the qualifier's own package-verification memory. No shell ulimit/prlimit
integration was independently exercised; the measured mechanism is the Python
resource/setrlimit-before-exec path retained in the exact harness.

## Reproduce on a disposable Linux namespace-capable host

Use a new absolute fixture path outside the checkout:

    python3 contrib/devtools/review-evidence/linux-worker-resources/prepare-fixture.py /absolute/new-fixture
    python3 /absolute/new-fixture/build.py
    python3 /absolute/new-fixture/guest-run.py

prepare-fixture.py copies and SHA256-checks the78exact upstream source/header
files, and the unchanged build/probe/harness inputs used in the VM. It creates no
node/wallet, installs nothing, starts no network service and expects existing
Python3/C/C++20tools. The CLI/probe binaries are built locally, not downloaded.
The driver runs12finitecases in fresh pinned packages. It leaves synthetic output
under the fixture for inspection; remove that disposable fixture when finished.
The fixture-preparation packaging step was checked locally by byte equality; no
runtime test was repeated during publication. Binary identity is host-specific.

## Limits and decision

This is supported owner-local execution with a tested existing bound, not proof
of public-network exploitability, host/node failure, default mining impact or a
new regression. No real model package, full node, release signing, Windows,
Ubuntu/glibc, aggregate descendant accounting, malicious limit-raising probe,
process-count limit or broader isolation guarantee tested. Our earlier PID patch
is not folded into these binaries and was not retested. Its process isolation
addresses a separate issue; adding memory/process policies remains a design choice.

No product patch is proposed. Built-in default size, policy/API and aggregate
semantics need agreement before a change. Fresh97PRtargeted overlap scan found
no equivalent item14fix; unpublished work is not ruled out. One packaging pilot
missed a relative cryptoheader; compiler refused it. Added exact upstreamheader,
no product edit; excluded from final runtime evidence. All fixtures removed from
our guest, no test process remains, VM stopped; production unchanged.
