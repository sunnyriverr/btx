# Finalized Ethereum refund maker cleanup — tested fix

Credit repch1c for native ETH→BTX reproduction in #630 latest point3: https://github.com/btxchain/btx/pull/630#issuecomment-6874643101 . Base f08e0b4b. Focused repair removes only the height-domain restriction from existing unfunded-maker refund closure; finality, canonical/exact/fresh observation and durable funding/grant/coinlock guards remain.

## Verdict

Identical maintained component tests:2failed6passed before,8passed after. Full candidate165passed. Independent bounded source review found no concrete safety defect. Tests use real signed coordinator negotiation and SQLite with simulated EVM observations.

Native Ethereum boundary: https://github.com/sunnyriverr/btx/actions/runs/43579229310 . Actual compiled SwapNetHTLC on Anvil1.9.0 plus production EVMDriver/EVMAdapter, coordinator and SQLite. Same native harness fails intended closure assertion on upstreamf08: finalized exact canonical refund, maker committed, active1, mandateheld20490 after reopening. Candidate releases held budget to0 and active slot to0, revokes unused grant, persists cancelled across reopening, and accepts a new proposal at127other fixture rows. Pre-finality refund remains unrecognized at finalized and held; durable local funding WAL control retains budget/position across reopen. Raw baseline statusINCOMPLETE reflects expected assertion failure; before.log identifies it precisely.

**BTX leg simulated.** This is not a full embedded two-node BTX/ETH swap. Local funding control inserts a durable WAL record; no new real funded BTX position was executed. Native Ethereum transactions use disposable Anvil unlocked accounts; automatic signing/gas/withdrawal are outside this check.

Checkpoint build https://github.com/sunnyriverr/btx/actions/runs/43579028797 restored prior combined Bitcoin candidate772b35d2 and relinked in11tasks. Its initial fixture import missedpytest; subsequent native run supplied it and reused checksum-identical binaries. The daemon compiled but did not execute this Python/Anvil fixture. Native source layers the one-line repair onto the earlier Bitcoin candidate; this focused product commit is independently based onf08.

## Evidence and reproduction

Product commit: 76d4ab56389848e91f2ec97e096388a53ec9ff6d. Maintained test: contrib/swapnet/tests/test_timestamp_capacity.py. With tested cryptography/pytest dependencies, run `python -m pytest -q contrib/swapnet/tests/test_timestamp_capacity.py`; expect2fail6pass onf08with test added,8pass on repair. Full suite: `python -m pytest -q contrib/swapnet/tests`.

Native check.py/run.sh/workflow.yml are the executed fork recipe; job checks production-source equality to b14b1b29, uses official hash-pinned Foundry release, compiled actual contract, then same harness onf08andcandidate. Reconstruct from the immutable CI branch94859cd2abf2e25033ffb98889dc6d06d39e5bd3 and run43579229310; artifact14107319527 SHA25669b9a8cfbf43ad317755673d00b9ecccd7e34a92d6268e22b16037e5aede744b matched downloaded bytes. Component/local and native receipts, raw results/logs, script and review included. No package/mainnet/release qualification.
