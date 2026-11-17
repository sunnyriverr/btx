# Reorg save-failure repair — native result audit

Reviewed run44031548060's raw `records/{baseline,candidate}/result.json`, build-result/plan/build/test logs, executed `repair/test.py`, candidate source and `source-identities.json`. Evidence audit only; no re-execution, build or product change by reviewer.

No scoped blocking contradiction found. The completed normal-helper Linux pair supports the reorg-only rollback/deferred-event repair.

## Exact before/after scope and identities

The baseline is the previously qualified normal helper with the existing #815 no-history guard, not unmodified bd847. The candidate is that guard baseline plus this save-retry repair. Both run the identical test SHA256 `9f7313520600c366f8b99208f7364312b1043564e763323f554a1dd28322f9e1`.

- Baseline binary: `f62fb21f1246658c04c437b96b228bf41f9552f7897e287c8183fa29082c50eb` (immutable reused qualified helper).
- Candidate binary: `79d69e9407e9e1150093a8feada25da0a850527234da248d9a990d99a211f333`.
- Baseline bounty source: `23ab54cd8c29efcdd8c8801ea014e792feb056af428d320644a90bc7424845d7`.
- Candidate bounty source: `66336bf9569e763bb2eed1aa60a2bba5fb8ed848b6fe1bb11d22b3d5337524ed`.

The final local candidate/test bytes match those source identities. Build-result source/test/binary identities agree with the raw candidate result and prior baseline identity. Candidate configure and ordinary `btx-modeld` link succeeded; the log shows31 bounded incremental actions, ending in the normal executable link. Checkpoint/external verification reports29,776 inputs and zero differences, with current tracked bytes verified. This is compatible-cache incremental qualification, not a clean whole-project rebuild. No Mac diagnostic controller/RNG adapter or dynamic-lookup path is in this normal target.

## Observed outcome

| Result | Guard baseline | Guard + retry repair |
|---|---|---|
| Status / test exit | EXPECTED_CONTRACT_FAILURE /7 | PASS /0 |
| Checks |21 failures,3 passes of24 |24 passes of24 |
| Cases / helper starts / RPC calls |7 /14 /144 |7 /14 /144 |
| UID / GID |65534 /65534 |65534 /65534 |
| Healthy first/remaining undo |100 then0, persisted0 |Same |

There are14 retained helper logs per variant. The final result is written only after all seven cases and their hard valid-control assertions complete; setup/control failures cannot count as expected contract failures.

For the first unkeyed permission fault, raw calls26–35 show baseline funding300/epoch5 before IO, then100/epoch6 after IO, a local corrective event and a shared-journal corrective event, and retry0/epoch7. Candidate returns the same exact IO refusal but retains300/epoch5, no local/shared corrective event, and retries once to100/epoch6. The same-key case reproduces that discrimination. The replacement case begins with A200 replacing A100: baseline IO leaves100 then retry deletes A; candidate IO preserves200 and retry restores A100. This proves restoration of a previous fact value, not only retention of a newly inserted key.

All five save-fault attempts in each variant establish same-user marker denial, exact `IO`, byte-identical durable JSON and no leftover temporary save. Candidate also preserves live facts/undo epoch and both event views; the baseline fails those checks. The unrelated S50 observation remains throughout. In all three retry cases the candidate retains exactly A:0 with amount100, commits one journal correction and survives an actual restart at100. Baseline retries persist0. The three baseline journal-count checks happen to pass because a premature failed event can occupy/dedupe that slot; they do not negate the21 other intended failures or constitute correct event behavior. Candidate's earlier no-failed-event assertions plus successful one-event checks discriminate that boundary.

## Legitimate controls

Both variants finish ordinary first and remaining undo, conditional re-observation, restart without retry, successful keyed replay and the unrelated write-policy case. Successful keyed replay compares exact prior result and unchanged disk/funding/journal. With the repair, IO leaves the complete pre-request300 state; re-observing A preserves300 rather than pretending an undo happened. Restart reloads the last committed300 in both variants. The unchanged #468 draft policy is explicitly verified: a refused draft save remains visible in memory, disappears on restart, and the earlier durable draft/local event behavior works. The repair therefore does not silently impose rollback on unrelated writes.

## Limits and decision

This is normal linked Ubuntu22.04-container/Linux x86_64 helper execution through real UnixRPC as an unprivileged user, including actual helper process restarts. Synthetic operator-entered watch-only observations, not actual-chain reconciliation, wallet funds, signing, mainnet, Mac/Windows or full-suite/release qualification. The fault is parent-directory permission denial, not disk-full/flush/power-loss. Post-commit allocation/journal exceptions and the cross-store crash window are not qualified; no durable outbox or undo-format change is added. One final matched test pair; diagnostic runs using stock/815 helpers are separate evidence, not additional repair pairs.

The scoped repair acceptance is supported: a refused bounty undo save leaves its undo/fact/event state retryable, and a successful retry performs exactly one undo while preserving valid controls. Any handoff should keep the #815 baseline/dependency and these practical limits explicit. Publication remains held.
