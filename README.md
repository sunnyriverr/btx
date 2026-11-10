# BCP/1 locked-wallet comparison

Both commands return misleading funding errors on release source `dac9aee53520bd49ed320ec7a49b9072fc7d88d9` with a funded, locked encrypted wallet. Both return an unsigned PSBT after unlock and also work on a funded descriptor wallet with private keys disabled.

| Command | Locked | Same request unlocked | Watch-only P2MR |
| --- | --- | --- | --- |
| `createexchangebatch` | `-4 Insufficient funds` | Unsigned PSBT | Unsigned PSBT |
| `createconsolidationtx` | `-4 Not solvable pre-selected input` | Unsigned PSBT | Unsigned PSBT |

The locked consolidation plan still listed the coin. The four decoded PSBTs each used the expected confirmed input, were incomplete and had no finalized input fields. The payer relocked, neither funding output was consumed, nothing was broadcast, and the temporary node stopped cleanly.

One completed Ubuntu 24.04 x86-64 regtest comparison using an unchanged packaged node and direct wallet RPC. The encrypted payer and watch-only wallet each held 5 synthetic BTX. Exchange used automatic inputs. Consolidation selected its own input. The watch-only wallet used an imported ML-DSA P2MR deposit and the default node-level exchange-watch-only setting. The watch-only `listunspent.solvable` flag was false. Both actual unsigned RPCs passed. Two earlier setup attempts ended before reaching these commands.

[Executed CI job](https://github.com/sunnyriverr/btx/actions/runs/42793024731) · [Exact fixture](https://github.com/sunnyriverr/btx/blob/5f9c6490b0070bb464aab5170fa321420e5a9677/contrib/devtools/bcp1-locked-wallet/run_bcp1.py) · [Workflow](https://github.com/sunnyriverr/btx/blob/5f9c6490b0070bb464aab5170fa321420e5a9677/.github/workflows/bcp1-locked-wallet.yml) · [Machine result](result.json) · [Provenance](provenance.json)

The run covers the two RPCs, with no candidate change applied. GUI, external signing, explicit input requests, other RPCs and platforms are outside its scope. It independently reproduces the two BCP/1 cases from repch1c's report. [Original report](https://github.com/btxchain/btx/pull/475#issuecomment-6762813554)
