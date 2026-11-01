# Linux cancellation component result

Completed 2026-11-01T07:18:10.086649+00:00. AI-assisted implementation/testing on real local Alpine3.22.4,
Linux6.12.81 aarch64, musl1.2.5, GCC14.2. Original run completed privately; this sanitized evidence is published by user authorisation.

## Result and decision

The identical final harness fails four shutdown fault cases on the original
70e35da0 supervisor/transport and passes all six cases on the corrected combined
candidate. Healthy and stubborn-owned controls pass both. Long getmodel calls
remain successful after123 seconds on both; application refusal propagates.
This supports the scoped Linux supervisor/transport behavior of the existing
candidate; it does not qualify a full Linux node build or all supported platforms.
No additional product fix was required.

| Scenario | Before | After |
|---|---|---|
| healthy_owned | PASS (0.171s observation) | PASS (0.176s) |
| partial_owned | FAIL (1.501s observation) | PASS (0.214s) |
| silent_owned | FAIL (1.502s observation) | PASS (0.216s) |
| stubborn_owned | PASS (5.155s observation) | PASS (5.174s) |
| external_partial | FAIL (1.502s observation) | PASS (0.055s) |
| external_backlog | FAIL (1.504s observation) | PASS (0.027s) |

Shutdown bound1.5seconds except the intended five-second escalation control,
which has a7second bound. Baseline fault observations are bounded failures, not
measured completion times: the fixture is released AFTER the deadline so cleanup
can finish. Full accept-queue pressure is proved by real AF_UNIX EAGAIN and a
paused accept loop. Partial/silent reply faults have explicit fixture markers.
External helpers survive, answer ping, and are reused with the same PID by a new
supervisor on both versions. Owned children are reaped. Long-call helper stays
alive while its supervisor stops; the independent getmodel caller completes.

before silent normal reply: 123.012842s; refusal INVALID_PARAMETER preserved.

after silent normal reply: 123.013849s; refusal INVALID_PARAMETER preserved.

## Exact build and scope

Both binaries compile the complete unchanged supervisor.cpp translation unit,
with original supervisor.h/profile/types/fs/compat/tinyformat and UniValue
sources. Transport compiles exact source-extracted CallUnixRpc, WaitFd, RecvUntil,
reply-timeout, socket-adoption and peer-credential function bodies. The corrected
candidate is the combined patch already linked in #354, including socket-error
channel correction. Only before/after source input differs; same final harness.
GCC command uses the repository's C++20 requirement, -O1 -g0 -Wall -Wextra -pthread.
No normal CMake target or full dependency graph is claimed.

Support adapters are explicit: minimal Sock declaration/RAII with original
SetNonBlocking function body, no-op logging/node advertised-bit update, ASCII
ToLower, scoped helper API declarations, and pass-through socket-path selection
for short private fixture paths. JSON parsing is real UniValue. No send/recv,
connect/poll, socket, spawn, signal or waitpid mocking. This is meaningful native
component execution, not compilation of full helper.cpp or production util target.
No actual btx-modeld/inference, btxd wallet/chain recovery, GPU, full suites,
sanitizers, Ubuntu/glibc, Windows, fallback path, or release qualification.
No separate real send-buffer saturation oracle was run; full ACCEPT queue and
read cancellation must not be described as complete write-backpressure coverage.

## Preparation and excluded pilot

Initial focused-build setup needed C++20 instead of17, additional original
support headers and the existing path-policy helper functions. Compile logs are
retained; no product test ran on those incomplete builds. First native pilot
completed most comparisons but pinged immediately after accept-queue release,
before the helper drained it, and hit EAGAIN. The control now waits up to5seconds
for actual helper reachability. Shutdown deadlines/oracles and product binaries
are unchanged. BOTH versions reran with the same corrected final harness.
See pilot-harness.py and guest/pilot-results; pilot is not counted as final.
Final is one complete paired matrix, not repeated3x qualification.

## Reproduction and preservation

prepare.py materializes the recorded baseline/candidate slices; input/build.sh
contains the focused guest build command. regression.py executes on the guest.
The helper fixture is synthetic, uses private local sockets and no model payload,
wallet or public traffic. source-identities.json records source/extraction/input
hashes; evidence-manifest.json fingerprints the curated files, binaries/logs.
Before binary SHA256: abbc038cef2b2539b91f10cc88493cf3a5878c4bff89a342b05ae4e76c574d6b.
After binary SHA256: e326b697e1e113eecd34d35a7b74d9e48628a62712b0de419fa5a231765a39cb.
Final harness SHA256: 282bb9981f89403fc079ca05409773986c281806467fdb9343994b60425703f3.

Cleanup check finds zero fixture/driver PIDs. VM stopped cleanly. Host source
still has only the original net_processing.cpp/peerman_tests.cpp changes; shared
build cache and production wallet/node/miners were untouched. Host free space is
approximately1.06GB; focused inputs are about233KB plus small binaries/logs.
No large build, deletion, rental, consensus change, new PR or post.

Stop: requested native component comparison complete privately. Further work
needs a concrete missing acceptance criterion; no repeat of this matrix merely
to increase counts. Windows, glibc and full dependency build gaps stay explicit.
