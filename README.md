# Spent deposit confirmation after reconnect

When a block containing an already-spent deposit disconnects and reconnects, the deposit stays SPENT. The notification path now treats its disconnect observation as a new confirmation when the transaction has positive depth.

On macOS arm64 regtest, the same maintained test received zero new confirmations after reconnecting the block on 51c11074 and exactly one with this patch. The existing ordinary deposit, multi-output reconnect and first spent-deposit confirmation checks passed.

Baseline 51c110744ff53dea081bb2967bb698b684136bb3 from repch1c's #528 on release base dac9aee53520bd49ed320ec7a49b9072fc7d88d9. Modelnet and Metal disabled in this local AppleClang build. The wrapper drops only Modelnet arguments on that build. No funded wallet or live chain. Both runs used the same extended functional test. The JSON files identify the executable, test and product hashes.
