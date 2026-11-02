# #377/#378: single ordinary RPC worker

AI-assisted scoped execution review by Sunny River. Production changes in this
branch are repch1c's exact #377 (49ceccfc) and #378 (1ef2142b) deltas on cbf65894.
This is a production-only test combination, not a new fix or competing PR;
the upstream PRs' new functional tests are not copied here. Source hashes and
compiled executable identities are in results.json.

## Observation

One final run per configuration on macOS26.5.1, AppleM4/arm64, AppleClang17,
normal CMake Release btxd/btx-cli/btx-modeld targets, ModelnetON, wallet compiled
ON but disabled at runtime. A real node-owned helper and height0 regtest;
no public P2P/model listener, LAN discovery, mining or wallet activity.

Same harness starts a valid15000ms waitformodelevent, confirms it in
getrpcinfo.active_commands, and measures getblockcount on a separate connection:
- rpcthreads1: getblockcount waits15.003s; getrpcinfo responds0.47ms.
- rpcthreads2: getblockcount responds0.38ms; getrpcinfo responds1.97ms.
- Both waits time out normally; subsequent ordinary calls and a fresh model wait
  work, node exits0 and its helper is gone.

#377 permits max(1,rpcthreads/2) forwarded calls; one worker therefore has no
ordinary worker reserved. #378 reserves capacity in the separate helper pool.
This is a configuration-boundary observation, not a new regression or a tested
failure of defaults. The ordinary measured call is getblockcount; wallet/mining
RPCs and P2P progress were not exercised. No baseline-without377 run, Linux,
Windows, default16 case, full-suite or release qualification. No product fix.

## Reproduce

Build the normal btxd, btx-cli and btx-modeld targets from this branch using the
repository's normal Release build instructions. Then run:

    python3 contrib/devtools/review-evidence/pr377-single-worker/reproduce.py --bin-dir /absolute/path/to/build/bin --out /absolute/path/to/new-results

The output directory must not exist. This uses bounded waits, fresh temporary
datadirs, disabled wallets and no model payload. It records observed latency
rather than treating the one-worker delay as an overall test-run failure. It
requires the real binaries, not a mock helper. Datadirs/cookies/identities are
removed at completion; logs remain local to the requested output directory.

## Setup and build limits

Reused owned CMake cache with normalized source and relevant objects rebuilt.
Two build attempts hit the disk safety floor while CMake regenerated ~380MiB of
dependency metadata. Only completed disposable regtest blocks and regenerable
build dependency metadata were reclaimed; original sources/binaries restored
afterward. One dependency-make placeholder was needed during regeneration.
Startup pilot maxmempool5 was correctly refused; final harness uses41 and an
explicit loopback RPC allowlist. No pilot counts as an observed product failure.

Question for the author: should the isolation promise explicitly require at
least two ordinary RPC workers, leaving one-worker serialization intentional?
Nothing here argues for rejecting all model calls at1 or silently changing the
operator's worker count. Detailed source/binary identity is in results.json.
