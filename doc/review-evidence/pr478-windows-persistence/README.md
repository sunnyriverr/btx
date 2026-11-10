# PR #478 — scoped native Windows persistence review

**Tested ACK `309ad5d2bb5f148aba22666fa8b7db2ced7ed08d` for the three cases below.**

JPP's production fix and maintained tests are unchanged. Base production is
`dac9aee53520bd49ed320ec7a49b9072fc7d88d9`, with the candidate test file applied
for the before observations. The same test source is used on both sides.

| `matmul_trusted_mirror_tests/` case | Before | Candidate |
|---|---|---|
| `local_pq_vote_persists_and_survives_restart` | Recursive-lock exception after setup | PASS, 10 assertions |
| `received_pq_votes_persist_and_survive_restart` | Recursive-lock exception after setup | PASS, 17 assertions |
| `attestations_survive_simulated_restart` | PASS, 11 assertions | PASS, 11 assertions |

The two baseline PQ calls exit 201 with `std::system_error: resource deadlock
would occur`, at the maintained SignAuthoritative/AddPq checkpoints after key,
configuration and database setup passed. This is not a measured 10-second
Windows hang. Source/checkpoint attribution is retained; no individual native
mutex stack was captured.

The candidate returns Accepted, restores the local vote/quorum at height 77,
and preserves the receiver's 2-of-2 quorum at 56 while 1-of-2 at 55 stays below
quorum, before and after store reset/reopen. The secp persistence control passes
both sides. All maintained assertions are intact.

## Results and exact execution

- [Per-case results, source trees and binary/object hashes](results.json).
- [Full executed command records](executed-commands.json), [native profile](profile.json),
  [test compilation](test-compile-command.json), [production compilation](node-compile-command.json),
  [archive inputs](node-archive-argv.json), and executable-link response files
  [before](baseline-link.rsp) / [after](candidate-link.rsp).
- [Exact source manifest](source-manifest.json) and [restoration receipts](restoration.json).

| Observation | Before focused log / XML | Candidate focused log / XML |
|---|---|---|
| Local PQ | [log](before-local-pq-focused.txt) / [XML](before-local-pq.xml) | [log](after-local-pq-focused.txt) / [XML](after-local-pq.xml) |
| Received PQ | [log](before-received-pq-focused.txt) / [XML](before-received-pq.xml) | [log](after-received-pq-focused.txt) / [XML](after-received-pq.xml) |
| Secp control | [log](before-secp-focused.txt) / [XML](before-secp.xml) | [log](after-secp-focused.txt) / [XML](after-secp.xml) |

Full `.log` files are alongside each focused log. Focused copies remove only
unselected-test skip messages. The three maintained selectors can be run with
`test_btx.exe --run_test=matmul_trusted_mirror_tests/<case>` on each composed
source; the exact native invocations and test-directory arguments actually
executed are in the command records. This shorthand is a reconstruction recipe,
not a separate reproduced run.

Windows Server 2025 x64, clang-cl 20.1.8/lld-link, Release optimization/static CRT;
wallet, Modelnet and tests enabled. Runtime backend CPU, one solver thread. The
original stock cache 10223164157 was restored and verified; only the named test
and production objects were compiled, with the saved library/link inputs.
No full clean build is claimed.

Six product-case executions in total; valid passing cases were not repeated.
The baseline secp/local observations come from
[42780444882](https://github.com/sunnyriverr/btx/actions/runs/42780444882), receiver from
[42782255924](https://github.com/sunnyriverr/btx/actions/runs/42782255924), and all candidate
observations from successful
[42782930409](https://github.com/sunnyriverr/btx/actions/runs/42782930409).
Fresh compilations in separate jobs have different object/binary bytes; the
per-observation identities are explicit. Only identical test source/profile is
claimed across jobs. All source, 5,901 objects and 12,858 cached files were
restored/hash-verified after every job; runtime and owned processes were removed.

## Setup history and limits

The first runner stopped on Windows' exception rather than classifying it as the
author's Linux deadline failure. A [separate, narrow Windows exception oracle](windows-exception-review.json)
was then checked against the actual log/XML and negative controls. Normal pass
classification remained strict.

Two avoidable runner assumptions caused extra setup: a cross-job object-byte
equality gate stopped [42781469813](https://github.com/sunnyriverr/btx/actions/runs/42781469813)
before any product case, and the archive extractor initially expected the
executable link's response-file form. These were corrected from the measured
commands; completed baseline results were retained. Total setup was six targeted
object compilations, one archive update and three executable relinks across four
jobs, each capped at 25 minutes with a 600-second work bound, 45-second outer
case bound and resource/process-tree cleanup. The last job ran only the three
remaining candidate cases.

“Restart” here means `ResetForTest()` and reopening the durable store. This does
not qualify actual node restart, concurrent `ClosePersistence`, mixed signers,
GPU/mainnet operation, the full Windows unit suite or a release. It adds scoped
Windows evidence for the existing fix; it changes no production or test code.
