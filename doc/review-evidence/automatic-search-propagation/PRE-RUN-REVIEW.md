# Automatic search runtime — bounded pre-run review

Source review only of the final runtime test/build/workflow/retention scripts. Product is pinned to `00cef6af17e331d503eb276933e1ec3e30395407`; the prior observation review examined unchanged helper/search behavior at0afc505. No execution, product change or publication by reviewer.

No decisive pre-dispatch fixture/API/build blocker found.

## Observation and controls

The receiver is fresh and receives no RPC during initial propagation. `launch` uses socket existence plus helper log readiness rather than a probing RPC. The helper-call allowlist permits receiver RPC only during `offline_restart_local` and only explicit LOCAL search or index listing. The no-contact control also receives no RPC, runs11seconds, has no configured publisher contact, and is checked externally for the expected IDs. Do not describe that finite negative interval as a universal network-isolation proof.

Seventeen uniquely identified signed records from a single fixture publisher exceed the automatic gossip's16-record page, giving a useful continuation/progress observation. The expected map comes from the publisher's raw local export and contains signatures/public keys. Receiver success requires exact persisted record objects, not just IDs/counts. The tiny index stays below the observation RPC's100-record cap. Passive reads do not call helper search. `observe_until` now hashes, parses and saves the same raw bytes for each recorded snapshot, avoiding mismatched hash/evidence reads during atomic replacement. An empty/malformed/absent file cannot produce the positive propagation result.

The publisher is stopped before receiver restart. The receiver's first allowed search uses exactly `scope=LOCAL`, which is the source branch that loads saved economy/index state without remote fanout. All four coverage counters must be zero, local result IDs must match all17, raw local export must match the full signed objects, and persisted index bytes must remain unchanged. This closes the known false-empty startup-memory problem without using an implicit NETWORK search or rescue import. It is an offline local-read/reload check, not zero background connection attempts: the configured receiver may still attempt its unavailable publisher from its own tick.

Publisher restart reuses its state and endpoint, publishes only record18, and requires passive receiver equality with all18 plus a single96-hex transport pin matching the earlier observation. Participation schema/zero-acquisition/zero-spend/LAN-disabled assertions match the inspected source. A six-second passive interval checks both helpers stay alive and exact receiver records remain, followed by clean stops. The same-pin observation is supported together with the newly propagated18th record and source authentication path; the saved participation data alone is not a per-handshake trace.

The fixture creates no receiver cloud/retrieve/watch state or model payload. A fresh helper still performs its ordinary local initialization and participation tick; those are the behavior under observation. It does not modify product code or shorten the tick. The reported result should remain metadata/search propagation, not model-byte transfer, WAN discovery, paid inference or general network readiness.

## Failure and process behavior

Unexpected startup, RPC, parse/schema, timeout or equality errors produce `UNRESOLVED_FAILURE`; read-only diagnostics cannot promote that to PASS. Cleanup stops only tracked owned helpers, verifies zero exit, and marks cleanup errors as failure. Result records binary/script hashes, actual process starts, RPCs, passive snapshots and remaining owned helper count. If the outer test timeout kills the harness before its `finally`, the workflow's owned-container removal is the final containment; do not claim per-helper clean shutdown for such a failed run. The successful path checks cleanup explicitly.

The exact publisher port is chosen from loopback then reopened, so an ephemeral bind race can produce a setup failure; it cannot be a false success. No public endpoint or production process is selected.

## Build and retention

The workflow independently checks out immutable accepted/current and checkpoint source. Archive hash, restored bytes/modes/links/timestamps and external toolchain inputs are verified before object reuse. Current tracked bytes are copied and reverified; removed old tracked paths stop the job. Input script hashes are asserted. Configuration requires ModelNet ON, a finite <=250-action normal-helper plan and sufficient restored headroom; no silent unbounded rebuild fallback is present. Only normal `btx-modeld` is built, with no diagnostic linkage or store adapters. Preparation, compilation and runtime have separate result states.

The test phase copies read-only executable/runtime/script inputs to a traversable `/tmp` directory and runs as UID/GID65534. This addresses the prior unprivileged checkout-path problem. Script/binary hashes are checked against the recorded build. The workflow uploads records on failure and removes only its named container.

`retain.py` only runs after a binary identity exists, records actual source/binary/stage, and uses the checkpoint helper's conservative space/unchanged-state checks. A test failure may still preserve the verified build for follow-through; its identity/stage must not be relabelled as a passing runtime. Retention failure is a resource/artifact issue, not evidence of a product defect. No new runtime, product changes or retries should be launched merely to turn an unrelated retention problem green.

The preflight is sufficient for the authorized single guarded attempt. Final claims require the actual records, exact source/binary/script hashes and the outcome of each stage; no runtime pass is implied by this review. Publication remains held.
