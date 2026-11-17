# Operator save ordering — independent repair review

**Verdict: no source/design blocker found in the three-move candidate.** Compared candidate/swapnet/application.py and embedded.py against sibling baseline and read the relevant constructor/factory/ready dependencies. No code edits, tests/imports, native execution, network or publication. This is source/design review; maintained tests are forthcoming and not qualified by this report.

## Asset driver publication

The candidate keeps owner, factory availability, active-obligation and readiness gates in their existing order. It prepares/checks the candidate driver, constructs the policy setting, commits that setting, then publishes the driver into the existing shared drivers dict. Application and Coordinator still refer to the same dict, so a successful assignment updates the supported consumer without replacing/losing its mapping. If set_setting rejects, execution never reaches the assignment; the old driver remains live and the old policy remains durable. A later successful same request can align policy and driver normally.

This is the correct narrow fix for publication before durable acceptance, not a new all-or-nothing transaction over provider preparation. Native Host.configure_asset/UTXODriver readiness reads provider/wallet state; EVMDriver.ready additionally invokes _account, which can create a foreign vault key and save an evm-account setting before asset_policies is committed (evm_driver.py:28–34). Those preparation effects were already present and remain possible when policy persistence fails. Do not advertise complete failed-request rollback, assert every settings row is unchanged for every real factory, delete prepared private keys or add account cleanup to this repair. The deterministic nonfunding factory can prove live-driver ordering, but does not qualify external readiness effects.

The baseline active guard uses the existing public journal prefix. The separate complete-reader repair owns that issue; this save-order diff does not modify or weaken the guard. Preserve/compose that independent adopted change as required by the parent's actual delivery source; do not rediscover its tests as a new requirement here.

## Explicit and automatic wallet binding

Host.rpc now saves the owner-validated, loaded wallet before caching it in _wallet. An initial save failure therefore leaves the host unbound, allowing the same healthy request to retry the actual write. The owner requirement, loaded-wallet check and later WALLET_SCOPE check are unchanged. Do not infer a successful real wallet operation merely from a thin-context Host.rpc result; the diagnostic correctly scopes that result to actual Python routing/control flow.

Host.selected_wallet likewise validates a list and exactly one loaded wallet, holds that selected value in a local variable, saves native_wallet, then caches/returns it. This covers the adjacent internal selection caller without changing its authorization model or adding a new wallet choice. On write failure there is no new live binding; on healthy retry the loaded list is checked again rather than trusting an unsuccessful prior cache mutation.

Known bindings still follow the previous fast path and loaded/scope checks. The constructor retains its exact precedence: explicit config wallet, otherwise durable native_wallet, otherwise unbound. Configured wallets are not newly forced into the journal, and a known binding is not rewritten on every read/RPC. This preserves explicit operator configuration and existing wallet isolation rather than attempting a broader binding migration. A running pre-repair process with already-divergent memory is not retrospectively repaired by source changes; normal restart/explicit lifecycle is separate from this new-call invariant.

## Commit/apply boundary and serialization

The supported native Runtime::Work executes Engine RPC, peer callbacks and tick serially. Journal.set_setting commits synchronously before returning; the following shared-dict or plain attribute assignment invokes no normal external callback. There is therefore no supported concurrent observer between policy/binding commit and its immediate live application. No new lock held over readiness/provider IO or multi-setting transaction framework is needed.

A process stop after commit but before the in-memory assignment leaves the durable desired value for later reconstruction. This review does not establish native reconstruction by execution, guarantee successful reply after arbitrary process death, or make memory/disk an atomic system under MemoryError/custom mapping/thread mutation. Such concerns do not justify undoing an already committed setting or expanding the narrow repair.

Market/withdraw/advertise code is unchanged. Their earlier compound partial-commit behavior and catalog/sequence effects retain the diagnostic's separate contract disposition; no claim of fixing them is appropriate.

## Focused qualification still needed

Use matched stock/candidate observable controls for existing asset policy and first asset insertion: after actual settings transaction rejection, old live driver/map and durable asset policy stay unchanged; after healthy same-request retry, the intended driver/policy agree and a new Journal reads the value. Preserve owner/active/not-ready refusals and shared coordinator-driver identity. Scope “unchanged” to the states the fixture actually records, not arbitrary factory side effects.

For both explicit Host.rpc and automatic selected_wallet: reject native_wallet saving, assert _wallet remains empty and durable setting absent, repeat failure if useful to expose a skipped-save implementation, then healthy retry durably binds the selected loaded wallet. Verify separate-journal/reopened binding data and legitimate known-binding/mismatched-wallet/unloaded/zero-or-multiple-loaded guards. Constructor-configured/durable binding precedence should remain source-identical; a lightweight appropriate caller control can qualify it without a full native wallet launch. Preserve original request/SQL error behavior rather than converting failed save to successful selection.

The existing healthy market/withdraw cases may remain compatibility controls, but are not before/after repair oracles for this patch. No broad native wallet, funded chain, full host restart, power-loss or extra platform gate is required to establish the local ordering contract. Record the actual qualification/source identities and remaining native limits before claiming completion; publication remains outside this review.

## Final candidate source/assertion review

**Final verdict: no blocking issue found in the supplied two-file candidate and18-case regression source.** Re-read both baseline/candidate production diffs and candidate/tests/test_config_save_order.py. Production code remains the same three save-before-live-assignment moves reviewed above. The parent reports matched stock6fail/12pass → candidate18pass and12 existing Application/runtime controls passing; these are the parent's execution receipts, not tests independently run by this reviewer.

The asset regression's one/two-failure parameterization asserts the original driver object remains in both Application.drivers and Coordinator._driver after every actual SQLite rejection, while the settings snapshot and a new Journal connection retain the old policy. Healthy retry must publish a different live driver carrying the new policy and persist the new setting. Wire/budget/funding-record assertions add appropriate fixture-level no-unintended-action controls; they are not a native accounting qualification.

Both explicit Host.rpc and automatic selected_wallet regressions use one/two failed writes. Every failure must leave _wallet empty and durable native_wallet absent, so a cache-only implementation cannot make the second attempt bypass persistence. Healthy retry must commit the selected wallet and then return/cache it; a new Journal reads that same value. A later conflicting explicit wallet must still receive WALLET_SCOPE with the selected binding unchanged.

The remaining12 cases are legitimate controls, explaining the reported12 stock passes: three asset owner/active/not-ready gates; seven wallet guards (owner, unloaded explicit selection, other-bound scope, zero/multiple loaded choices, invalid wallet-list type and bound-but-unloaded automatic selection); and existing durable binding in both entry points without resaving. The owner case confirms no listwallets call before refusal. The existing-binding cases run under the same rejecting trigger, so they distinguish the intended no-rewrite fast path from accidental persistence on every use.

These assertions directly test the proposed observable contract, not only helper return values. Trigger removal and retry use the same app/host objects, making the previously poisoned in-memory state relevant. Reopen is a second real Store/Journal read; it is explicitly not full Host.__init__, native activation or configured-wallet reconstruction. Constructor precedence remains unchanged in the source diff. The synthetic active agreement and deterministic Driver/listwallets fixture remain sufficient for the local guard/ordering claims; they do not exercise actual wallet/provider setup or EVM _account side effects.

No market/withdraw contract change, rollback of EVM preparation, native funding, full host restart or power-loss result is implied. The earlier side-effect/serialization/commit-boundary qualifications remain part of the final verdict. With the parent's recorded matched/control results, the focused repair can proceed to its authorized local closeout without a new expensive gate; publication authority remains separate.
