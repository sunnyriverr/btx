# SwapNet maker recovery after a finalized ETH lock

One public BTX→ETH regtest case on the saved macOS ARM64 BTX daemon at `a97af7b3f379e33e3ec65db948468d875ade2841` and local Anvil (chain 31337). The taker went offline before the maker's ETH lock. Once that original lock finalized, the maker restarted in recovery-only mode. Both recovery restarts refused switching to taker or maker.

- The early refund returned `REFUND_EARLY`. At the timelock, the original lock was refunded and **0.009999 ETH** was withdrawn to the maker's original wallet. Both receipts were canonical and finalized. There was one lock, one refund and one withdrawal, within the agreed fee caps.
- The maker mandate's held budget dropped from 0.015999 ETH to zero and stayed zero after reopening. The contract balance and withdrawal credit were both zero. Four shared control socket startups passed. All test processes stopped cleanly. The controller exited 0 in 42.799 seconds.

The BTX leg stayed funded throughout. This run used the serial CPU diagnostic profile with Metal and ModelNet disabled, test MatMul settings and accelerated Anvil time and finality. It covers recovery of the ETH leg only.

[Selected native receipt and checksums](receipt.json) · [Fixture delta](fixture.patch) · [Previously executed settlement fixture and saved-input recipe](https://github.com/sunnyriverr/btx/blob/7d0354eff8d3b4bf4a078efee8cb85450db33be9/doc/review-evidence/public-market-eth-a97/README.md).

Reconstruction uses the prior fixture and matching BTX daemon, Anvil, pinned contract and Python runtime. Apply `fixture.patch` in the fixture directory, update the local manifest's `public_eth.py` hash from the receipt, set `cases` to `["eth-lock-recovery"]` and choose a fresh empty short runtime path through the controller (the named path must be absent before launch). Keep the original disk and 600-second bounds. The executed command was `python3 fixture/run_prepared.py --execute eth-lock-recovery`. The other three fixture files were byte-identical to the prior published copies.
