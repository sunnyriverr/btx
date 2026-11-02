# #338 item18: helper-worker descriptor lifetime

Bug: an owner-configured resident loader retains the helper's TCP listener after
an intentional helper crash. A replacement keeps local RPC working but cannot
restore its network listener. Original code-read finding: repch1c. AI-assisted
candidate and macOS tests: Sunny River. Existing descriptor utility retains its
upstream authorship. No new PR; code commit is separate from this evidence commit.

## Results and limits

Identical real-helper regression: resident restart FAIL before3/3, PASS after3/3.
Idle/no-worker and unload/restart controls pass once per build. Optional inference,
generation stdin/JSON, llama argv/stdout and generation exit37 error recovery pass
once each on both builds. Child socket inventory is empty on the patched build.
Synthetic finite adapters only: no real CUDA or model inference, Linux/Windows,
full-suite, node-supervisor, PQ1 transfer, mainnet or release qualification.

Recorded builds compile the full helper.cpp TU and relink with identical cached
CMake dependencies on macOS26.5.1/M4, AppleClang17. Their baseline is cbf65894 plus
#37749ceccfc and #3781ef2142b (tree45db5cca), not a fresh full clean-base build.
The code commit on cbf65894 contains the identical five added lines. Full commands,
source/binary identities, raw sanitized results and limitations are in build.json,
branch.json and REPORT.md. Report's local-directory references refer to this evidence
layout; original private reports/pilots remain archived locally.

## Reproduction

Use disposable local test processes only. This harness SIGKILLs only the helper
it starts, uses loopback, disables LAN/NAT/peer-following/seeding, and removes its
temporary model/identity directories. Never pass production data paths. Native
adapter fixture has a45second lifetime and opens no socket itself. SO_ACCEPTCONN
is unsupported on this Mac; getsockname/fcntl plus lsof are the observation oracle.

From this directory, build only the two tiny test adapters:

    clang -std=c11 -D_DEFAULT_SOURCE -O1 -Wall -Wextra -Werror ../helper-worker-inheritance/adapter.c -o ../helper-worker-inheritance/adapter
    clang -std=c11 -D_DEFAULT_SOURCE -O1 -Wall -Wextra -Werror control.c -o control

Use separately built original/candidate btx-modeld binaries with the same build
settings/dependencies. To recreate the recorded production source combination,
start at cbf65894 and apply the src production deltas of #37749ceccfc and #3781ef2142b;
then add candidate.patch only for the candidate. Their RPC-admission changes are
not part of this fix. The patch also applies to clean cbf65894.

    python3 reproduce.py --binary /absolute/original/btx-modeld --out /absolute/new-before --cases resident-crash,resident-crash,resident-crash,idle-crash,unload-crash
    python3 reproduce.py --binary /absolute/candidate/btx-modeld --out /absolute/new-after --cases resident-crash,resident-crash,resident-crash,idle-crash,unload-crash
    python3 controls.py --binary /absolute/original/btx-modeld --out /absolute/new-controls-before
    python3 controls.py --binary /absolute/candidate/btx-modeld --out /absolute/new-controls-after

Before command must exit nonzero for the closure/restart assertions; candidate
must exit0. Result pass means scenario/cleanup completed, while regression_pass
also requires no inherited listener. Baseline unload's stronger closure predicate
fails before unload, although its unload/restart itself succeeds. Do not count it
as a second restart failure. Harness uses macOS lsof; port to Linux for native
verification before claiming it there. Adapters intentionally report zero device
bytes and smoke_passed=false: helper protocol fields are not GPU qualification.

## Requested independent check

Linux full build and native before/after resident-loader restart, inference and
both generation paths; stdio, unload and worker-error recovery. Windows needs its
actual supported build path checked: this candidate uses a POSIX utility declaration.
Maintainers may prefer a public descriptor utility over the existing internal one.
No claim is made about intentional fd-passing contracts beyond stdio or reduced
RLIMIT_NOFILE edge cases in the existing utility. No need to repeat unrelated RPC,
transport or consensus tests just to review this finding.
