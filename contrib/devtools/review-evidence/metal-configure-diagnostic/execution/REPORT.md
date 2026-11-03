# Metal configure diagnostic — completed local handoff

PASS on current `cbf65894e6d61084527cd93e913a00c6794418dd`: native CLT-only
configuration accepted missing basic Metal tooling before the patch and failed
at the required metallib target; the source-reviewed patch rejects the same
selection during configure with an actionable stage-specific diagnostic.

Owner: **BTX test 1**, delegated executor `/root/metal_configure_execution`.
The coordinator owns shared records and any later branch/publication.

## Patch and source

Native product files are `product/src/CMakeLists.txt` and
`product/doc/build-osx.md`; apply `metal-configure.patch` to the exact target.
Approved patch SHA-256:
`d77b5adeadb739efa101c55a2e6e9625ce6db8648e7e0f34baf7596e81e2dcf3`.

The existing Apple + Metal + precompile ON + found-xcrun branch now checks a tiny
default-language compile, then a metallib link, before adding required targets.
Each required probe has a 30-second timeout, quoted paths, exact success-result
and fresh-output checks. Errors identify the stage/result, bound the tool
diagnostic to 2048 characters, point to setup documentation, and name the explicit
OFF runtime option and compiler-service requirement. The existing optional Metal
4 probe remains nonfatal and retains its prior timeout behavior; only its path
arguments are quoted and its tiny source is reused. A concise note is attached
to the existing docs precompilation paragraph to avoid overlapping #344's setup
rewrite.

Source came from immutable `git archive`, never the shared dirty checkout or its
Git caches. `source-file-identities.json` checks all 14,271 tracked files against
the target Git blobs: only the two approved product files differ, plus the exact
expected `.gitattributes` export-subst expansion in `src/clientversion.cpp`.
That archive expansion was present in both variants and is not a product change.
PR #344 head `7e26d77b82cc6ae1719e67ac5d6d4224426666cf` has an identical Metal
block, but surrounding OpenMP/docs differ; execution was current swarm only.
The original request is repch1c comment `6542655967`; their separate macOS report
is not counted as our native execution.

## Actual observations

All seven completed full-project configure cases used the same local profile:
Release/Unix Makefiles, native AppleClang, `/opt/homebrew`, Modelnet/wallet/GUI/
tests/bench/extra tools OFF, Metal ON except its gating control. Daemon remains
ON. WITH_ZMQ remains default ON and resolves static ZeroMQ. The available static
libomp archive is selected; **no serial-prover override** was needed or passed.
The separate minimum-Python warning disables already-OFF utilities/tests and did
not prevent reaching Metal or successful configuration. No prerequisites were
modified or bypassed.

| Case | Actual observation |
| --- | --- |
| Native baseline CLT, precompile ON | Configure exit 0; optional Metal 4 unavailable status; Metal ON; required six basic targets registered. |
| Same baseline, only `btx_matmul_metallib` built | Exit 2: `xcrun` cannot find `metal`; required `matmul_accel_kernels.metallib` fails late. No node compilation. |
| Native candidate, identical ON profile | Configure exit 1 in **basic Metal compilation**, result 72; native missing-utility text and explicit OFF/setup hint. |
| Native candidate, precompile OFF | Configure exit 0; runtime fallback status; no probe source/output or metallib target. |
| Recording basic tools available / Metal 4 unsupported | Configure exit 0; exactly default compile → metallib link → optional Metal 4 compile; six required targets and basic defines retained; optional targets/defines absent. |
| Recording compile succeeds / metallib unavailable | Configure exit 1 in **metallib linking**, result 72 and fixture-specific diagnostic; exactly two invocations. |
| No-xcrun tool-selection control | Cached empty dispatcher value; full project configures with existing no-xcrun runtime status, no probe/targets/invocations. This controls CMake selection, not native PATH discovery. |
| Metal OFF control | Full project configures; deliberately rejecting dispatcher is never invoked; no probe/targets. |

Every completed observation was executed once; no completed configure was
repeated to increase counts. An earlier candidate configure was interrupted
before Metal when the resource monitor raced with removal of a CMake temporary
file. The monitor was corrected; the interrupted pilot is retained separately.
Two observation assertions were corrected for CMake summary padding/line
wrapping, then consumed the already completed recorded runs without repeating
them. Initial archive extraction compatibility/symlink pilots are also retained
in `pilot-notes.txt`. These are harness issues, not product failures.

## Reproduction, limits and resources

`REPRODUCE.md` documents the actually executed `reproduce.py` baseline/candidate
entry points, exact target, dependencies and expected outcomes. The final runner
hash is recorded in `summary.json`; baseline ran an earlier observation-only
revision with the same configure/build command, before the recorded assertion
and resource-monitor corrections. The final candidate invocation resumed its
completed native ON observation and ran all remaining controls. There is no
claim of a separate clean replay of an unchanged matrix.

Native platform: macOS **26.5.1**, arm64, AppleClang **17.0.0.17000603**, CMake
**4.4.3**, CLT developer directory, Boost **1.92.0**, static ZeroMQ **4.3.5**,
static libomp. Selected SDK and exact tool/library hashes, full configure logs/cache/graph/
defines, probe hashes, recording invocations, commands/results/timing and input
identities are retained. This is focused local integration, not the release
profile. Fixture AIR/metallib files are text and do not qualify actual Metal,
Metal 4, full Xcode, runtime compiler availability, GPU execution, packaging,
full-node linkage or another platform.

Completed-run minimum sampled host free space was **1,999,896,576 bytes**
(1.86 GiB), above the 1.25 GiB floor; maximum sampled task logical size was
**163,494,639 bytes** (155.9 MiB), below the 350 MiB bound. Sampling was every
0.25 seconds; allocated file blocks differ from logical bytes. One configure or
single target job ran at a time. Only reserved output changed. No install,
download, VM/GPU/node, shared cache/index/ref, Git commit/push, external post,
spend, or production action occurred. Existing stopped tasks were untouched.

Regenerable owned builds are removed after relevant snapshots. Full isolated
source is removed after its identities and two native product files are retained;
the entry point can regenerate it from the exact Git object. Cleanup receipt and
final artifact hashes accompany this report. The next owner is the coordinator
for integration and any explicitly authorized publication after final artifact
review; there is no automatic new test or post.
