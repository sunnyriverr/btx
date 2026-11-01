# Linux PID isolation candidate — private tested fix

1 November 2026. AI-assisted native component investigation; no new PR or production change.

## Change and design

A focused one-file patch to the Linux filesystem jail adds CLONE_NEWPID to its
existing user/mount/network isolation. A trusted namespace-init process supervises
the actual worker, reaps children while waiting, and exits when the worker finishes;
the kernel then tears down remaining descendants, including ones using setsid().
The host-visible wrapper forwards the real worker's wait status through a private
CLOEXEC status pipe. Existing exec/setup error-pipe admission remains in place.

The worker is PID2, not namespace init. Running the worker directly as PID1 would
change ordinary default signal handling. A blanket signal-syscall ban was rejected
because legitimate workers must be able to signal their own children. Dedicated
host UIDs/cgroups would require new deployment authority/configuration. This patch
uses the already required Linux namespace facilities and preserves the public API.
It is a small scoped candidate, not a proof that no shorter correct design exists.

Base: unchanged #346 `a74b8af89e4121e80b64c942483d01021047dc7d`
filesystem-jail TU, with unchanged #337 `e3d87faf566ed9bef714e2eb9fefcd4236c66da9`
process-guard header. Both baseline and candidate use the same real support headers,
compiler, worker binary and final harness. No syscall/sandbox/filesystem adapters.
This is an identified component-source combination, not an official integrated ref.
The earlier fresh80-PR source/ownership scan is in ../linux-worker-isolation;
no matching PID/signal isolation fix or claimed owner was found there. It is not
an assurance about unpublished work or every other source file.

## Final identical harness:60 cases

Alpine3.22.4/aarch64/musl, Linux6.12.81, GCC14.2, ordinary guest UID501.
Compile actual full runner TU using C++20,-Wall,-Wextra,-Werror,-O2,-pthread.
The synthetic worker is static-musl. Build only runner changes between controls.
Three repetitions of each of ten scenarios on each build:

| Scenario | Before | After |
|---|---|---|
| External same-UID sentinel signal |Safety assertion FAIL3/3: sentinel exits42 |PASS3/3: ESRCH, sentinel survives |
| Detached child after normal worker return |Cleanup FAIL3/3: heartbeat continues |PASS3/3: heartbeat stops |
| Detached child after worker wall timeout |Cleanup FAIL3/3: heartbeat continues |PASS3/3: timeout returned, heartbeat stops |
| Ordinary worker/output |PASS3/3 |PASS3/3 |
| Invalid target PID control |PASS3/3 |PASS3/3 |
| Fork/wait child with known exit17 |PASS3/3 |PASS3/3 |
| Worker exits37 |PASS3/3, raw status9472 |PASS3/3, same status |
| Worker self-SIGTERM |PASS3/3, not falsely marked executed |PASS3/3, same result classification |
| Signal own child, handle signal and wait for exit19 |PASS3/3 |PASS3/3 |
| Invalid executable/setup error control |PASS3/3, JAIL_ABSENT |PASS3/3, JAIL_ABSENT |

Baseline:21 safety passes and9 expected safety failures. Candidate:30/30 safety
passes. Final harness SHA256:
`a67c940257814270967dff030fc4dbf25ac4bffd0fbf4f237482e8840c5f407e`.
Same static worker binary SHA256:
`4ba081343ea2aed3aa8c55369d0246f10b6098c419791b98f16c598e0e79478b`.
Runner/source hashes are in guest-identities.txt. final-runs.txt records each
assertion and exit code; verified-results.json is mechanically checked against
expected failures. Patch applies cleanly to the exact #346 file and reproduces
the tested candidate bytes (patch-check.json).

The existing outside-marker and live-host-loopback checks remain denied whenever
a worker completes normally. Sentinel PIDs are deliberately supplied; no arbitrary
host process is targeted. The baseline detached fixture has finite6second lifetime;
the harness waits7seconds after observing a leak so it does not leave test activity
behind. Patched cleanup has a100ms heartbeat observation after runner return.
Final guest process inventory found no remaining probe/baseline/patched processes.

## Pilot correction and limits

The first broader pilot used /proc executable-path enumeration as its cleanup
oracle and reported no leftovers despite a detached process potentially being
unobservable there. It is retained as pilot-runs-proc-only.txt and NOT used to
claim cleanup. The final harness adds a continuous heartbeat and catches baseline
normal-return and timeout leaks3/3 each. Both builds were rerun with that identical
final harness. This was a test-oracle correction, not a hidden product fix.

No full BTX CMake/test_btx, actual model workload, mainnet, Ubuntu/glibc, other
architectures, sustained fork load, parent-node crash, ptrace/pidfd exploit or
independent review was executed. Runtime classification preserves normal/nonzero
exit and signal-failure behavior in measured cases; the public API discards signal
status for refused execution, so no RPC proof of the exact terminating signal is
claimed. No native Windows/Mac behavior changes.

PID namespace unavailability fails the existing setup gate by construction; an
unsupported-kernel forced-failure run was not performed. The inspected execution
entry remains explicit native qualification, not unauthenticated peer dispatch.
This fixes a demonstrated permitted-worker boundary and cleanup case; it does not
establish public-network exploitability or settle all sandbox/resource contracts.

## Preservation and next step

Patch/evidence remain local. Shared source, original dirty files and build cache
were never edited. VM is stopped; no rental, dependency install, consensus/wallet/
node/miner change, GitHub post, message, commit or new PR. The candidate needs
independent native review and normal project integration before any release claim.
Do not expand into resource-limit work or repeat these cases without new need.

## Build this branch

In a disposable Linux VM with unprivileged namespaces and GCC/C++20, use the two sources here and the actual src/ headers. Preserve the exact base for a before control:

```sh
mkdir -p /tmp/btx-isolation /tmp/btx-isolation-fix
git show a74b8af89e4121e80b64c942483d01021047dc7d:src/modelnet/swarm_fsjail.cpp > /tmp/btx-isolation-fix/baseline.cpp
g++ -std=c++20 -Wall -Wextra -Werror -O2 -static contrib/devtools/review-tests/linux-pid-isolation/probe.cpp -o /tmp/btx-isolation/probe
g++ -std=c++20 -Wall -Wextra -Werror -O2 -pthread -Isrc src/modelnet/swarm_fsjail.cpp contrib/devtools/review-tests/linux-pid-isolation/harness.cpp -o /tmp/btx-isolation-fix/patched
g++ -std=c++20 -Wall -Wextra -Werror -O2 -pthread -Isrc /tmp/btx-isolation-fix/baseline.cpp contrib/devtools/review-tests/linux-pid-isolation/harness.cpp -o /tmp/btx-isolation-fix/baseline
```

The compile recipe maps the measured component inputs to their normal branch paths; this full-tree checkout recipe was not independently rerun. Compiler/tested source identities are above. Run each binary with a fresh absolute root below /tmp/btx-isolation and mode0..9 three times. Baseline modes1/6/7 intentionally return1; patched modes0..9 all return0. Do not use set -e to abort the expected baseline failures. Full CMake/node integration and the separate SwarmRunConfined path remain unqualified/unchanged.
