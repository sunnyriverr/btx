# Restored Ethereum pending-payment disposition on f40eb37a

**PASS at the tested Anvil scope:** a restored committed-session backup recovers same-lock fee replacement, local drop, and cancellation, with one effective lock and successful restart/refund. No product code changed and this is not an ACK of all #630.

This follows Numair's [pending-lock qualification gap](https://github.com/btxchain/btx/pull/630#issuecomment-6885658927). It does not make a mempool-only payment visible to `latest` or establish universal Ethereum client/network behavior.

## Exact execution

Production source `f40eb37a6fb8b665340fe92a2f248ff3f23ec7f6`: coordinator, EVMDriver, SQLite, authenticated encrypted bundle export/restore and SwapNetHTLC. Native Anvil/Foundry 1.9.0 on Ubuntu 24.04; BTX counterleg simulated. Disposable local accounts/test ETH only. Existing recovery fixture reused; no BTX compilation. Source hashes and artifact digests are in provenance.json.

| Control | Ordinary restored-session result | New fund operations | Effective Locked events |
| --- | --- | ---: | ---: |
| Same-nonce higher-fee identical lock | Pending duplicate gas estimation refuses; after mining, adopts the actual replacement hash, preserving deterministic lock identity. | 0 | 1 |
| Original removed from this local pool | Verified locally absent with nonce 0 available; retry funds once at nonce 0. | 1 | 1 |
| Cancellation pending | Retry funds at nonce 1; cancellation and funding mine, with one HTLC lock. | 1 | 1 |
| Cancellation mined before restore/retry | Successful same-nonce self-transfer receipt and absent lock verified before restore; retry funds at nonce 1. | 1 | 1 |

All four controls retain the actual funding reference through SQLite reopen, reach finalized refund/withdrawal, and reopen in `refunded`. Escrow becomes zero; the fixture's 1 ETH principal returns, with sender balance loss exactly matching all included funding/cancellation/refund/withdrawal receipt gas. Funding operations are excluded from the separate recovery-gas sum to avoid double counting. See summary.json and the complete per-case results.

## Executed entrypoints and reuse

- [First three controls, run 43674049900](https://github.com/sunnyriverr/btx/actions/runs/43674049900), wrapper `a9b50720ecab31aad302ea259dd2f66298967c16`.
- [Mined-before-restore cancellation only, run 43674219692](https://github.com/sunnyriverr/btx/actions/runs/43674219692), wrapper `779c3234e898fc065321d0d24ed57bb10680a44c`.

The exact workflows, run.sh and check.py are copied into recipe/43674049900 and recipe/43674219692. They check out the unchanged product source, verify the pinned Foundry archive, build the unchanged contract, start a fresh Anvil per case and run the production coordinator against it. The second run closes the precise mining/restoration cut; it does not repeat first-run passes. Native artifact ZIP digests were independently verified before results were inspected.

Foundry distribution SHA256: `8d17599b42e3139f1a9c171be3798c4ed8e743ae17b84cc3435e57bf2a51ae99`. Deployment runtime hash in every case: `a06e30bad714ff02db5a2401a898bd7194d1c475b61bdab312ae194b1509e45d`. Python direct fixture dependencies cryptography 46.0.4/pytest 8.4.2 reuse the earlier recipe; this is not a fully hash-locked Python distribution qualification.

## What this does and does not establish

The demonstrated recoveries require no repair. The coordinator's existing latest-state existence lookup still cannot see a mempool-only lock. On this Anvil profile, duplicate pending lock gas estimation refuses until mining, then the mined replacement is recoverable. Other node estimation/pool policies may differ. Dropping a transaction locally does not prove it disappeared from every node.

Accounting evidence covers operation/nonce identity and actual principal/gas reconciliation. Authority/reservation/budget totals were not independently asserted. The production authorization, deadline, signer, finality and deterministic lock checks were retained; there is no policy bypass. The native EVM leg does not qualify a full native BTX cross-chain swap, public network, real funds, package or release. No product patch or broader release verdict follows from the green job badge.

Jpp-matata's #692 contract coverage and existing healthy settlement/recovery evidence are reused rather than repeated. This tests restored coordinator/mempool transitions, not another contract test sweep. Internal bounded harness review found no clear causal blocker and required the narrower budget-accounting language. All test processes/stores were cleaned up.
