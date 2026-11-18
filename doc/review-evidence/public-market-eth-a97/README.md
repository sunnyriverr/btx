# Native public BTX→ETH settlement and restart on a97af7b3

**PASS — 90.787s, one corrected financial execution on macOS26.5.1 ARM64.** Saved clean node/CLI source a97af7b3f379e33e3ec65db948468d875ade2841; no rebuild or product patch. Native BTX regtest + Anvil31337, actual chain calls/signatures/transactions; no simulated chain responses.

## Outcome

- Signed firm public offer arrived through native peers → requester-bound quote → inert default-taker preview → explicit owner confirmation. Preview left balances, coin locks, sessions, EVM pending nonces and taker mandates unchanged. Confirmation retries reused one swap and one-shot mandate; maker slot transferred once.
- Both nodes restarted after original BTX funding had1confirmation, **before ETH funding**. Original outpoint/mandate/confirmation retry survived. This does not qualify interruption after ETH funding.
- Both parties completed. Finalized canonical Ethereum funding/claim/withdrawal receipts match the pinned contract, exact lock/payment/beneficiary/calldata/events. Exactly one original funding operation per side and one ETH withdrawal; zero remaining credit and zero contract balance.
- Exact BTX and ETH account deltas were independently reconciled against actual transaction fees/gas. Terminal restart preserved exact operations, budgets and balances; held budgets0 and no coins locked.
- **All6 shared-control startup checks passed:** active native status available=true, exact regtest network, wallet_authority=false, actual Unix socket and no startup-failure warning. Uses short fresh data roots, unlike the earlier BTC fixture's path-length limitation.
- Exit0, no600s/time/storage bound hit, process group absent, Anvil exited and cleanup[]. Disposable private runtime retained locally.

| Amount | Exact value |
| --- | --- |
| BTX original funding | 10,000,000 atoms |
| BTX recipient | 9,991,000 atoms |
| BTX funding / claim fees | 7,834 / 9,000 atoms |
| ETH contract payment | 9,999,000,000,000,000 wei |
| ETH actual recipient net | 9,885,351,999,204,464 wei |
| ETH funding / claim / withdrawal gas | 142,967,001,000,769 / 66,320,000,464,240 / 47,328,000,331,296 wei |
| Total ETH gas | 256,615,001,796,305 wei |

Budget used_atoms records reserved authorized amounts; it is not the measured chain-fee total. terminal_slot_history=[] is a nonexpired-view result, not proof that historical rows were deleted.

## Exact evidence and reuse

- [Native result](results/native.json), [bounded controller receipt](receipts/native.json), [controller progress](logs/controller.log).
- [Executed fixture](fixture/public_eth.py), [bounded controller](fixture/run_prepared.py), unchanged reused [BTC/native helpers](fixture/btc_helpers.py) and [EVM receipt verifier](fixture/evm_verify.py).
- [Binary/contract hashes](inputs.json), [current-source compatibility](source-compatibility.json), [provenance and exact original hashes](provenance.json), [internal read-only review](internal-result-review.json).
- [Saved clean build, profile and Python dependency evidence](https://github.com/sunnyriverr/btx/blob/dff0050ab37e05d83a765bb2a0329bf98cc0fb09/doc/review-evidence/public-market-native-a97/README.md).

Saved btxd SHA256 e762f614eaf2c3fe78f4bc88d593f88dfd754527d078056a2311e671c9b366ab. Anvil SHA2568c4fd5befae13e12a94848673c0705a73e985387e48a10ffe73a03a1d5defbb4. The retained contract source/ABI/foundry settings match a97; solc0.8.24, optimizer200, Shanghai, bytecodeHash none; deployed runtime Keccak a06e30bad714ff02db5a2401a898bd7194d1c475b61bdab312ae194b1509e45d. No Solidity rebuild was needed.

Credits: Numair's SwapNet implementation, Jpp-matata and repch1c's prior native lifecycle/contract reports. Earlier private/direct ETH results were reused as evidence and fixture foundations, not repeated as a direction/refund/soak matrix. The distinct boundary is the new public-offer/default-taker entry.

## Setup disclosure and limits

The [first setup-only attempt](receipts/startup-only-attempt.json) stopped at12.687s before offer/funding: fixture expected runtime_broker from an unused adapter. Active src/swapnet/node.cpp returns available/network/wallet_authority. Corrected that exact test contract, preserved the real socket assertion, re-reviewed and used fresh disposable roots. The earlier evidence-root mismatch was caught before native execution. These were fixture errors, not reproduced product defects.

**Diagnostic serial-CPU profile:** Metal/ModelNet/GUI off, explicit regtest MatMul activation overrides, accelerated Anvil finality and independent test-chain clocks. No ETH-funded interruption, ETH refund, GUI, public-chain provider, default-policy, full-suite, packaging or release qualification. One corrected financial execution; no multi-run reliability claim. No production funds/wallets used.

## Reconstruction

This branch retains the exact product source. The four fixture Python files are byte-identical to those executed. [manifest.example.json](fixture/manifest.example.json) is a labelled reconstruction example, **not the executed manifest**. Supply the identified saved binaries, matching Python framework/crypto dependencies, retained exact compiled contract artifact and a fresh unique short /private/tmp/se-* root, then save the example as fixture/manifest.json. The controller verifies artifact/fixture hashes and launches only on explicit --execute settle. No package install, compiler or implicit cloud dispatch occurs. Source assertions and hashes are reproducible inputs; fresh-machine reproduction has not been independently run.

Private wallets, cookies, databases, node logs/descriptors and binaries are not included.
