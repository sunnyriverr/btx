# SwapNet terminal journal polling

Tested candidate on 8d6d8b1aabf371b12f2b1f5797b950fed7962d4e (#630).
Credit to repch1c for reporting repeated saves of completed swaps in
https://github.com/btxchain/btx/pull/630#issuecomment-6866329324.

The journal now returns the existing revision when an already complete or
refunded record is identical apart from updated_at and per-leg observed_at.
Expected-revision, owner, agreement and irreversible secret checks run first.
All meaningful changes retain the existing transactional save and audit path.
The coordinator continues observing the chains and running recovery and EVM
withdrawal callbacks.

Ten unchanged ticks previously added 20 saved revisions and 20 audit entries
for a completed or refunded initiator, even with time frozen. With the fix,
unchanged polls add zero entries, including after observation times age beyond
the freshness limit and after reopening SQLite. Durable timestamps remain at
the last meaningful snapshot; decisions still obtain fresh driver reports.
Changed confirmations persist, and a simulated rollback of the contract spend
after reopening triggers claim or refund recovery that survives another reopen.
Existing funding, prepared operations, closed budget and secret-exposure state
are preserved.

## Execution and reproduction

The same final regression file on macOS arm64 / Python 3.11.14 produced:

- Original journal: 5 failed, 11 passed. [Baseline log](final-baseline.log).
- Candidate journal: 16 passed. [Candidate log](final-candidate.log).
- Full candidate Python suite: 131 passed. [Full log](repair-full-suite.log).

From contrib/swapnet with the matching Python dependencies installed, run
`python -m pytest -q tests/test_terminal_observation_persistence.py`, then
`python -m pytest -q` for the suite. For the baseline comparison, retain the
same added regression file and restore only swapnet/journal.py from 8d6d8b1a.
The final pair used those same commands and immutable source/test hashes in
[the receipt](receipt.json). [Original measurement](measurement.json) and
[patch](terminal-save.patch) are retained.

Tests use the existing simulated-chain Pair fixture and real SQLite on Mac.
The EVM check exercises the coordinator's withdrawal callback with a test
double. There was no native daemon, Bitcoin Core or EVM integration run for
this patch. Application of the adjacent maker-capacity patch was checked only
as a dry run; combined execution was not performed.
