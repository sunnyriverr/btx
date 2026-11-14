# PASS — original pending Ethereum payment adopted and refunded

14 November 2026. Production candidate #630 d7b9594b1d6f0b69fc743341725ae04cbf9681fb, unchanged. Harness-only fork commit830b5a275c476f087448211b6fbc4e107b830350. [Native run43585211622](https://github.com/sunnyriverr/btx/actions/runs/43585211622). Exact hashes and assertions: completion-receipt.json; measured states/receipts: pending-result.json. Artifact14109916796 downloaded, SHA256 checked and its raw JSON matched the job log.

## What happened

1. Exported an authentic encrypted committed-stage backup: account/authority/secret present; funding reference, operation and nonce records absent. Broadcast original1ETH contract funding with automining disabled; original remained pending and latest getSwap had no stored lock. Original coordinator/store stopped before restoring the old snapshot into a fresh directory. Original identity context was retained; no two owners ran together.
2. Restored preparation saw no lock at latest, but Anvil's pending-aware gas estimate refused the duplicate with AlreadyExists selector0x23369fa6. No second prepared funding record, nonce or broadcast was recorded. No additional retry gas was charged. This is an endpoint-specific observation, not a guarantee that every Ethereum endpoint estimates against pending state.
3. Mined the original. The restored production coordinator adopted the exact original txid, deterministic lock id and salt; no new fund operation was made. Restart preserved that reference and funded/recovery-ready state. Contract observation was exact, canonical and finalized. Exactly one Locked event existed.
4. Advanced controlled chain time to maturity. Production refund and withdraw operations both succeeded, using nonces1 and2 after original funding nonce0. Original principal1ETH returned to its original approved beneficiary. Contract balance became0. Gas: funding227551383140600wei + refund80334330702704wei + withdrawal55754556899706wei =363640270743010wei (0.000363640270743010ETH). Starting1000ETH minus final999.999636359729256990ETH exactly equals gas. No principal loss or second successful lock demonstrated.
5. Restart after withdrawal retained refunded stage, original reference and both recovery records.

## Actual impact and limits

The latest-only pending discovery gap remains in source. In this tested Anvil workflow it causes a transient preparation error, followed by successful original-payment adoption after mining. It did not require a product fix to recover. Contract deterministic-id/AlreadyExists protection is separate from pending discovery. Do not call this a universal mempool-recovery fix, mainnet test or a proof that no endpoint can broadcast a reverted retry. No dropped/replaced original, reorg, spent-history or unavailable-RPC qualification.

Native Ubuntu24.04 x86_64, Python3.12, pinned Foundry/Anvil1.9.0 and Solidity0.8.24; actual deployed contract, production EVMDriver/EVMAdapter/coordinator/authority/SQLite/export/restore. Simulated BTX counterleg, fixture identity/native-wallet context retained separately; no embedded btxd/P2P, actual BTX wallet restore, full swap, public Ethereum, package, power-loss or release qualification. Anvil finality is accelerated with slots-in-an-epoch1. Fixture uses explicit10s settlement/reveal margins and candidate's600s planning headroom, disposable fee mandates and gas balances, not default network timing.

The local RPC wrapper preserves Anvil's JSON-RPC errors as RuntimeError; higher-level embedded RPC/UI presentation of that refusal was not exercised. Automatic scheduled retry was not proven: the harness explicitly ticks preparation after mining. Restarts close/reopen production coordinator/store while Anvil remains running; not process power-loss.

## Pilots and reuse

f08 pilot43584401664 stopped during contract deployment finality setup; corrected by mining3 blocks after deploy. f08 pilot43584499390 reached pending restore, observed estimate refusal and original-lock lookup, then stopped on UNSAFE_TIMEOUT. Its pending/receipt evidence retained, not called a recovery pass. Current candidate already supplies600s headroom; no product patch or weakened deadline check was introduced by us. Final run uses unchanged candidate with additional exact-adoption/restart/refund/balance assertions, not a matched before/after repair claim. Prior ordinary swaps and cleanup tests were reused, not rerun.

## Disposition and next step

Requested scoped investigation is complete locally. Product unchanged; no upstream comment/PR. No repair justified by this result alone. A short evidence handoff, if authorized, can narrow Numair's known pending limitation to endpoint behavior and show recovery once mined. Do not expand into arbitrary endpoint simulations or repeat passing controls absent a named decision. Any future endpoint-independent pending policy is a separate maintainer decision.

Learning: distinguish a pending discovery miss, pending-state gas estimation and contract-level duplicate rejection. Track exact payment identity and final principal/gas balance through recovery before describing financial harm. The earlier deadline pilot was blocked by an already-known candidate change; reconcile those prerequisites before another run.

## Executed entry point and attribution

The exact successful workflow is `.github/workflows/pending-evm-recovery.yml` at tested commit830b5a275c476f087448211b6fbc4e107b830350, executing `bash ci/pending-evm/run.sh`. It checks out that commit into `product` and uses the maintained fixture modules from its unchanged candidate. Harness: `ci/pending-evm/check.py`; pinned tools/dependencies and cleanup: `ci/pending-evm/run.sh`. These files are retained unchanged in this evidence branch. The docs-only child commit was not another native run.

Credit Numair for the original-lock adoption code and repch1c for the earlier backup-recovery reports. This is scoped AI-assisted verification, not a product patch or a general ACK of #630.
