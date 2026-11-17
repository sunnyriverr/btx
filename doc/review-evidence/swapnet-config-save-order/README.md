# Asset policy and wallet binding save order — matched Mac evidence

Qualified repair at `8d93204bf9d200e0d7b54a79eb835a3308968929`, based on `release-0.34.17@371013d61dc124a363521df5b94e97f64d2464f2`.

A rejected asset-policy save previously left the prepared driver in the shared live map while the old policy remained saved. Initial explicit and automatic wallet selection assigned _wallet before saving native_wallet; after failure, a healthy retry reused the cache and skipped persistence again. The three changes save first, then publish the shared driver or initial binding. Guards and pre-existing binding/constructor precedence remain unchanged.

## Executed qualification

macOS26.5.1 ARM64, Python3.12.14, pytest8.4.2, cryptography46.0.4.

| Inventory | Exact stock3710 | Candidate |
| --- | --- | --- |
| Identical maintained18-case test | 6 fail / 12 pass,0.37s | 18 pass /0 skips,0.38s |
| Existing Application runtime/recovery workflow checks | Not repeated | 12 pass /0 skips,1.05s |

The six failing cases represent three publication sites (asset and both wallet paths) at one/two rejected writes, not six distinct bugs. Both source roots use identical test bytes, SHA-256 `42b18cf05328b78fca3e73f4dc55f3d769a9526b728f79f1c5a682b13dfd32cd`. Loaded production roots/hashes are asserted and captured in the run receipts. The public code bytes are independently verified against those tested hashes; the local extracted-tree commit in qualification.json is not a full upstream-tree revision.

The regression uses actual Application.rpc, Host.rpc/selected_wallet Python bodies, Journal and Store. SQLite TEMP triggers reject only the selected settings INSERT, exercising actual transaction rollback. On failure, the previous shared Application/coordinator driver and saved policy stay in place, or an initial binding remains unset. Healthy same-request retry persists and publishes the desired selection. A new Store/Journal connection reads the correct persisted policy/binding; this is not a full native Host restart.

Controls preserve owner authority; one synthetic active-obligation guard; candidate readiness; loaded-wallet, empty/ambiguous/malformed list and bound-wallet scope checks; existing durable bindings without resave; unchanged fixture budgets and no deterministic funding or rejected-path peer sends. Existing normal Application wire/recovery checks also pass. The existing history-completeness guard proposal (#805) remains separate.

## Scope and preparation boundary

Drivers/factories and native listwallets replies are deterministic test callbacks, using the maintained apps/Driver fixtures. No actual wallet, verifier endpoint, chain, C++ runtime, settlement or funding is contacted. Source confirms an unbound host is supported by default-empty -swapnetwallet, but this is not native constructor/startup qualification.

Production factory/ready is not guaranteed side-effect-free: EVM readiness can create account key material and its separate account setting. These legitimate preparations are retained. The repair protects publication of the live driver/target policy and initial wallet binding, not total rollback of all setup effects. Real EVM preparation was source-reviewed, not exercised by the fake driver. No change to market/withdrawal advertisement semantics, transactions/signing policy, schema or platform APIs.

SQL rejection is not an actual disk-full/fsync/kernel-crash/power-loss test. No Windows/Linux, native full restart, full suite or release qualification.

## Execution and reconstruction

Executed local entry point: `run_repair.py before`, `after`, `controls` under Python3.12.14. The archived runner has personal paths redacted and records source provenance.

Portable reconstruction recipe (not separately executed): use stock3710 and 8d93204bf9d200e0d7b54a79eb835a3308968929 checkouts, copy only `contrib/swapnet/tests/test_config_save_order.py` from candidate into stock, install the Python dependencies above, then run in each isolated checkout:

```sh
PYTHONPATH=contrib/swapnet:contrib/swapnet/tests python3.12 -m pytest contrib/swapnet/tests/test_config_save_order.py -q
```

The existing-control target was `contrib/swapnet/tests/test_runtime_recovery_v2.py` using the same environment. Use only disposable test directories, no production node/wallet.

[Qualification](qualification.json), [stock log](before.log), [candidate log](after.log), [existing controls](controls.log), [independent source review](REPAIR-REVIEW.md), [published manifest](MANIFEST.json). The review is independent agent source/assertion review, not a second platform execution. This evidence excludes the earlier diagnosis of compound market partial commits, which is a separate contract question.
