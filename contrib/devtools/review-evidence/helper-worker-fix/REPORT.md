# #338 item18 — tested local descriptor-closure candidate

**The same real-helper restart regression fails before and passes after the fix,
3/3 resident-worker crash cases on each side.** Replacement helpers recover their
TCP listener while the worker remains alive. Local RPC also stays available.
No publication or push. Original finding: repch1c.

## Candidate

One product file, five added lines: include `util/subprocess.h`, then call the
existing `subprocess::detail::subprocess_close_all_fds(-1)` after each child's
stdin/stdout/stderr pipe setup and before exec. Covers resident CUDA-loader protocol,
optional inference command, generation adapter and llama command. The utility already
has Linux close_range support with a descriptor-loop fallback. No new policy,
process signal, worker timeout, node/consensus change or library dependency.

Private local branch `codex/modelnet-worker-descriptors`, code commit
`b9e1a19c4707ff05e3e7cab4979137819e46c7a9` on swarm `cbf65894`.
`candidate.patch` is the tested delta; `committed.patch` is the same five-line change
on the clean base. Branch is not pushed. Commit credits repch1c's report and AI
assistance. Tests used the existing #377/#378 combination described below; this is
not a claim that a fresh clean-base full build was run.

## Results

| Workflow | Before | After |
|---|---|---|
| Resident loader alive across helper SIGKILL; replacement gets network listener | FAIL 3/3 | PASS 3/3 |
| Idle helper crash/restart | PASS once | PASS once |
| Explicit unload then helper crash/restart | PASS once | PASS once |
| Inference command output and unload | PASS once | PASS once |
| SafeTensors generation stdin -> JSON output | PASS once | PASS once |
| GGUF llama argument/stdout path | PASS once | PASS once |
| Generation worker exits37 -> NOT_RUN; subsequent local RPC and shutdown | PASS once | PASS once |

The identical `reproduce.py` was executed with each binary. The before command
returns assertion failure; the after command exits0. Raw `pass` means harness
workflow/cleanup completed; `regression_pass` measures descriptor closure and TCP
restart. The baseline unload case also has `regression_pass=false` because its
worker inherited a listener *before* unload; its actual unload/restart control
passes. Do not confuse that extra closure-property failure with an unload failure.

`before/`, `after/`, `controls-before/`, `controls-after/` contain results and logs.
The patched resident worker has only stdio descriptors in lsof and no sockets in
its getsockname inventory. Baseline workers inherit the helper listener. On baseline
crash, replacement logs bind failure while its local RPC responds. On candidate,
replacement owns the exact TCP port even before releasing the surviving worker.
The controlled surviving worker exits normally after release. All helper shutdowns
outside the deliberate crash return0. Idle and explicit-unload controls use the same
helper options and port selection strategy.

The additional real-helper controls use tiny local SafeTensors/config and GGUF
fixtures patterned on repository hosting tests, plus native synthetic adapters.
Adapters wait1second, preserving a nontrivial call duration. Local RPC responds
during that wait. The inference case uses real loadmodel -> loader + optional infer
exec, then unloads the loader. Generation verifies prompt on stdin and expected
JSON text; llama verifies argv prompt and text; exit37 remains a structured failure.
Patched inventory is empty of sockets in every child path; baseline controls expose
inherited descriptors while their legitimate results still work. These are adapter
protocol/lifecycle tests, not real GPU inference or performance measurements.

## Source, build and overlap

Fresh GitHub inventory still97openPRs through379, no changed heads since the full
item18 review. No equivalent correction identified. #354 covers node->helper,
not helper->worker. See `overlap-refresh.json` and prior
`../helper-worker-inheritance/overlap.json` for checked revisions/coverage.

macOS26.5.1/M4, AppleClang17. Baseline helper source is production tree
`45db5cca94751e59ac09b8f05e165ae24988a2f4` (swarmcbf + #37749ceccfc + #3781ef2142b).
Compiled the full unchanged/helper candidate translation units separately using the
existing CMake-generated Release flags, copied the existing modelnet archive into
each private directory, replaced only helper.cpp.o, and relinked the real helper
with the existing CMake link command. Both use identical cached dependent libraries.
**Focused compile/relink, not a fresh complete CMake build.** Direct compilation
and linking succeeded on both sides. `build.json` records commands and identities:

- Before: `133c234c1227888531093fe99a526e29139439ae05780e1c2cb45ef73a00f55d`
- After: `9f883affc75c77f6ba80641cd87bb215d8ec667c3cf816ef839d1fdfe026f1a6`

The existing helper/fixture source and initial measurement-probe correction are
preserved under `../helper-worker-inheritance`; none of those original artifacts
were overwritten. No new product-fix pilot was needed. Before/after tests use
corrected getsockname/fcntl observation and independent lsof, not unsupported
SO_ACCEPTCONN as the listener-state oracle.

## Scope and remaining verification

Native Linux build/execution and Windows compatibility remain unverified. Existing
utility's POSIX declaration is excluded on Windows, and this helper's current
POSIX implementation is the tested path; do not call it Windows-qualified. Reusing
an internal detail utility is a reviewable minimal choice; maintainers may prefer
a separately exposed descriptor helper. No actual CUDA, inference/model quality,
PQ1 transfer, btxd supervisor restart, full-suite, mainnet, release or arbitrary
operator adapter qualification. One-second controls do not qualify24h calls.
Existing process-group/parent-death/timeout behavior was preserved in source;
timeout/signal-escalation suites were not rerun. No API promises for intentional
inherited descriptors beyond stdio are introduced.

All owned processes reaped/exited, disposable identities/model directories removed,
ports released. Shared dirty source, build source, original binaries and cached
objects/libraries untouched; private archive/object copies only (~88MiB total).
No wallet/node/miner/VM touched. User **no posting yet** remains active.
Disposition: local candidate and evidence complete; next is review/handoff of this
finding, not another investigation or duplicate tests.
