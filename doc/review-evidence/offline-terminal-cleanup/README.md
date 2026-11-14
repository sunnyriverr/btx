# Offline refund terminal-budget cleanup

Base ea63f560f41c7922095ec723f1e415a3babc280a. Three added coordinator lines and one maintained five-case regression. AI-assisted.

Interruption after the refunded-stage commit but before reservation settlement leaves a funded reservation. While the Bitcoin cookie remains unavailable, the already-refunded branch previously returned before retrying cleanup. The candidate retries idempotent Authority.terminal after rechecking maturity, fresh canonical exact settled refund evidence, matching original durable refund and confirmation depth. No new spending authority is created.

## Maintained regression

Apply cleanup-retry.patch on the base. With Python3.11 and existing SwapNet dependencies, run from contrib/swapnet:

    python -m pytest -q tests/test_offline_terminal_cleanup.py
    python -m pytest -q tests

The same focused file on the unpatched base:2 failed,3 passed. Repaired full suite:154 passed in25.42s. The cases interrupt before cleanup, inside its transaction and after successful cleanup, then reopen/retry; they retain consumed budget/grant, original operations and chain transaction counts. Unconfirmed/noncanonical refund controls retain the budget. Logs attached.

## Native execution

Native Mac arm64 executable based on cb823a94 plus this retry, with12 changed/header-dependent production translation units and frozen current package rebuilt; other C++ archives reused, then relinked. Not a clean build. Real native two-peer negotiation/funding/refund; no seeded negotiation state.

The run was paused by disk reserve checks during confirmation mining. The identical binary and stopped case were verified/checkpointed and resumed after cache cleanup. The final continuation confirmed the same refund to20 blocks, verified a fixture SQLite abort had left refunded/funded state, flushed chainstate/index, SIGKILLed the native process and restarted from the same datadir. Tip and confirmations were unchanged. With Bitcoin stopped again, removing the abort trigger allowed reservation closure. Original fund/refund pair, consumed grant/used budget, payout ownership and audit were verified.

Bitcoin was available during startup driver qualification, then stopped before cleanup. This does not qualify continuous Bitcoin unavailability across boot. Chains were on an HFS+ RAM volume retained across process restart, not a power-loss test. Complete ea63f560 was not run natively; its offline cleanup helper matches the native-tested cb823a94 helper apart from this repair. Other native platforms and EVM were not tested.

Native fixture/continuation are archived executed local harnesses, not maintained functional tests or a portable one-command recipe. They assume the original task-local binary/dependency layout. The reproducible maintained entry point is the Python test above. build-receipt.json and native-result.json identify the native execution. Personal path prefixes in supplemental files were replaced with placeholders; no private wallets, raw signed transactions or credentials are attached.
