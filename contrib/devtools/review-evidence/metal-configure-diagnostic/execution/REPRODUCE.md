# Metal configure regression

Target: `cbf65894e6d61084527cd93e913a00c6794418dd` (`btx-035/swarm`).
`metal-configure.patch` is the native two-file source patch. The Metal block is
identical at PR #344 head `7e26d77b82cc6ae1719e67ac5d6d4224426666cf`, but its
surrounding OpenMP code/docs differ. Apply this patch to the stated current
target, not to the old PR head without adaptation.

Use macOS with working C/C++/Objective-C++ CLT compilers, CMake >=3.22, Unix Make,
pkg-config and the normal BTX native dependencies already installed, including
static libomp, Boost, Libevent, ZeroMQ and OpenSSL. This recipe performs no
installation or network fetching. It requires at least 1.25 GiB free throughout
and limits its own work directory to 350 MiB. The actual executor used CMake
4.4.3, AppleClang 17, macOS 26.5.1 arm64 and `/opt/homebrew` prerequisites.

Run these two phases against an existing Git repository containing the exact
target object. Choose a fresh work directory outside the supplied evidence:

```sh
python3 reproduce.py --repo /path/to/btx --work-dir /path/to/fresh-metal-check --phase baseline
python3 reproduce.py --repo /path/to/btx --work-dir /path/to/fresh-metal-check --phase candidate
```

The optional `--cmake /path/to/cmake` and `--prefix /path/to/prefix` select existing
tools/dependencies. Keep the two phases' choices identical. The entry point
assembles a complete source tree with `git archive`, so unrelated dirty checkout
files and Git caches are excluded. Candidate applies only the supplied patch.

Baseline expects real CLT-only `xcrun` to exist but lack `metal`: full project
configure succeeds, then the sole `btx_matmul_metallib` target fails with the
missing utility. Candidate expects the same configure to fail early with the
basic compilation stage and actionable hint. It then configures with real CLT
and precompilation OFF, and uses a recording dispatcher for basic-success /
Metal-4-unsupported, missing metallib, no-xcrun and Metal-OFF controls. The last
two assert no dispatcher invocation or metallib target. Controlled compiler
outputs are text fixtures, never native Metal binaries or GPU qualification.

This is a focused local configure profile: Modelnet, wallet, GUI, tests and extra
CLI/tools are OFF; daemon remains ON; WITH_ZMQ stays default ON. Static libomp is
used as available. No serial-prover override is passed, no full node is built,
and no runtime compiler/GPU, daemon-service, release packaging or non-Mac claim
is made. The source includes complete project logic; only the one baseline
required-kernel target is built. Regenerable configure directories are removed
after their logs, caches, target graph, backend defines and probe hashes are
preserved.

The exact executed native baseline is retained in `logs/baseline*`; command,
return code, elapsed time and sampled resource bounds are in each adjacent JSON.
Pilots and harness corrections are in `pilot-notes.txt`.
