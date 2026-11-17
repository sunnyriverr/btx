# Native BTX/ETH verification after PR777 regression repair

**PASS on `cd3078e76398b20b7f500acd1348a5b5455f3d5e`, including Numair’s `b921fc5e` fix.** JPP identified and bisected the regression; Numair repaired the native not-found classification. This receipt closes the subsequent real embedded-callback check, not a new code proposal.

| Real native check | Result |
|---|---|
| BTX-long first funding → BTX/ETH claims/withdrawal | PASS, 52.416 s |
| Exact BTX funding output/claim/payout, fees, wallet deltas, ≥20 confirmations | PASS |
| Actual Anvil canonical/finalized funding, claim and withdrawal; pinned contract and gas caps | PASS |
| Both completed sessions/operations after clean restart | PASS |
| Maker BTX first funding; counterparty stopped before BTX confirmations; original payment after maker restart | PASS |
| Early refund refused; output unspent at590; original refund admitted at591 and confirmed ≥20 blocks | PASS |
| No duplicate funding, exact refund payout/fees/wallet delta, terminal restart | PASS, 66.805 s total |
| Owned nodes/controller groups and Anvil cleanup | PASS |

[Machine qualification receipt](qualification-receipt.json), [settlement](records/settle/result.json), [refund](records/refund/result.json), [runtime](records/runtime-result.json), [settlement log](records/native-settle.log), [refund log](records/native-refund.log).

The saved native daemon SHA-256 is `13389baef507e90f7724235ab799453832fa78fefac8abf924df2fb84a671438`; its compiled C++ callback and frozen Python were rebuilt for the pinned source in [build44053621896](https://github.com/sunnyriverr/btx/actions/runs/44053621896). Artifact14315282277 outer/inner/inventory and every selected restored file were verified. [Restore receipt](records/selective-restore.json), [dependency inputs](records/dependency-inputs.json), [source/build manifest](manifest.json).

## Executed path and limits

Executed `python3 native-runtime/run_local.py` in the retained workspace. It invoked the matched private Python3.12.10 controller as `python3.12 -B -u native_pair.py <disposable-case-directory> settle` and `refund`. The controller performs all BTX actions through public RPC into two actual embedded btxd processes; it imports only read-only EVM ABI/receipt helpers externally. Product source, native adapter, signer and coordinator were not simulated or patched. Source: [native_pair.py](native_pair.py), [EVM verifier](evm_verify.py), [local runner](run_local.py).

The runner requires the retained `local/` source/binary/runtime layout, verified Foundry1.9.0, and exact Solidity contract output. This is the executed retained-artifact recipe, **not** a claimed turnkey clean-checkout build. The controller's environment contract is `BTX_BINARY`, `BTX_BINARY_SHA256`, `CONTRACT_ARTIFACT` and `ANVIL_URL`; CWD supplies `product/contrib/swapnet` and `records/`. The published scripts are unchanged executed scripts. The original machine receipt binds original file hashes; `published-manifest.json` separately hashes these copies and records any path-only redaction.

One run per case on macOS26.5.1 ARM64 using a saved macOS15.8.2 build, private hash-matched Python3.12.10, SQLite3.49.1 and OpenSSL3.0.16. Real native BTX regtest plus Anvil EVM; serial CPU diagnostic profile, MetalOFF/ModelNetOFF, delayed MatMul activation heights. No mainnet, full suite, default MatMul or release qualification. The refund case proves the maker’s BTX short leg; it does not follow the later EVM long-leg refund.

Accelerated independent chains initially caused an `UNSAFE_TIMEOUT` refusal; continued EVM progression restored the conservative margin and settlement completed. Deadline, finality and confirmation guards were unchanged. BTX was not rebuilt locally; only the pinned Solidity contract was compiled and its creation/runtime hashes checked. Foundry lint warnings remain in [contract log](records/contract-build.log). Two prior hosted attempts failed before execution for ARM runner capacity. The local launcher corrected unsupported `--silent` to supported `--quiet` before tests. No system installation or real wallet use.

BTX settlement locked10,000,000atoms, funding fee7,834, claim fee9,000 and recipient9,991,000. Maker refund paid9,990,000atoms with funding fee7,834/refund fee9,000. Fee checks stayed below500,000atoms; exact chain IDs/outpoints/transaction hashes are in the receipts. Wallet files, RPC cookies, raw signed transactions, witnesses and private keys are not included.

Controller reuses Sunny’s existing two-node funded fixture; JPP’s native bisect supplied the missing boundary and Numair supplied the product repair. Prepared and checked with AI assistance.
