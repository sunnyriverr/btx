# Maker slot after confirmed counterparty refund

Session 3 claimed roadmap priority 5. Target: #630 at `8d6d8b1aabf371b12f2b1f5797b950fed7962d4e`. The prior Session 2 refund run tested the initiator with the maker offline. This run exercises maker observation and incoming proposal admission.

**Result:** a confirmed counterparty refund leaves the unfunded maker's slot occupied through restart. The production SwapNet Python coordinator, journal and database ran with the maintained Pair fixture. Its BTX/BTC ledgers simulate confirmations, with a configured threshold of two. Real SQLite stores were closed and reopened. No node, real wallet or real funds participated.

- The taker constructed and sent its recorded refund at simulated maturity. At zero and two confirmations the maker saw the exact refund and stayed `committed` with `wait_for_chain`. At two confirmations the initiator reached `refunded`. The maker had prepared and broadcast nothing and held 20,490 simulated atoms. Restart and another tick preserved the maker state and hold.
- With 127 explicitly synthetic occupied rows plus the stuck swap, a fresh signed proposal failed at the real SQLite gate with `ACTIVE_LIMIT`. Removing one synthetic row let the same proposal reach `offered`. This checks admission at the capacity boundary, not settlement of the new swap.
- A noncanonical refund at the same depth retained the hold and active slot. In the funded control, a maker restart preserved the funding and refund operations. The maker broadcast its own refund at maturity, retained its funded reservation while pending and released the slot after its own refund reached two confirmations.

The source routes a sufficiently confirmed **local** refund to the terminal path. An unfunded responder seeing its counterparty's refund falls through to `wait_for_chain`. A repair needs a proven absence of local funding, including durable funding operations that may outlive session flags, and a defined response to reorgs. A simple stage change would be insufficient.

Three focused checks and all 118 Python suite cases passed. The focused checks assert the observed baseline behavior, including the defect. An initial funded-control pilot advanced only one simulated chain and hit the deadline check, so the final control advances both. A second setup pilot needed the parent temp directory created.

Native BTX/Bitcoin Core regtest was not run. The retained native fixture uses a Linux build and a separate watch-wallet prerequisite. The Mac had about 1.27 GiB free, close to the 1.25 GiB reserve. The coordinator result is local evidence for designing the next regression, not native adapter acceptance. No product code was changed. Nothing was posted.

Next: qualify the maker-online native regtest fixture, then design and test the transition with durable-operation and reorg controls before any proposed handoff.

## Native BTX refund and candidate test

The baseline and candidate probes both exited 0 with a real native BTX regtest HTLC refund at height 110 and two confirmations. The real UTXO driver inspected the funding outpoint and its spend. The fixture routed that observation into the actual maker coordinator, used fixture clocks and a simulated Bitcoin leg, and reopened the maker's SQLite store before ticking it. With 127 synthetic occupied slots, the baseline kept its original hold and rejected the next signed proposal with ACTIVE_LIMIT. The candidate closed its reservation and admitted the next proposal as offered. An unconfirmed refund left the maker committed in both runs. [Baseline](native-paired-baseline.log) · [Candidate](native-paired-candidate.log).

The candidate closes the unfunded responder and revokes its unconsumed grant in the same transaction as the reservation release. It uses a locally observed, sufficiently confirmed canonical UTXO refund. Local funding flags, references, durable operations, coin locks or a consumed grant prevent release. The old agreement remains cancelled if the remote spend is later rolled back, so it cannot authorize new funding.

Five focused tests run as part of the 120-case passing Python suite. They cover next-proposal admission, noncanonical evidence, funded recovery, a durable fund record with stale session flags, and atomic rollback on an injected database-path failure. The same focused file against the baseline had two expected failures and three passes. Startup pilots corrected an unsupported ModelNet flag, an overly strict descriptor import assertion and the probe's RPC error adapter. Product policy and real wallet data were untouched.

The paired run does not cover native embedded SwapNet peer transport, a Bitcoin Core regtest node, or real BTC/BTX settlement. The BTX refund is native; the admission result is for the production coordinator with fixture proposals and real SQLite. [Candidate patch](maker-terminal-capacity.patch) · [Receipt](candidate-receipt.json). Everything remains local.

Next: review the terminal and recovery semantics and run the same maker-online test with embedded SwapNet and a native Bitcoin Core regtest node before proposing a handoff.

## Native embedded SwapNet with Bitcoin Core regtest

Ran the stock and rebuilt BTX v0.34.16 daemons on arm64 macOS with embedded SwapNet and Bitcoin Core v30.4.0 regtest. Both chain drivers reported ready. The probe seeded a committed maker agreement and its hold in SQLite. The native BTX regtest node verified the actual HTLC refund and the embedded worker observed it while the maker was online. The test restarted the maker at 19 confirmations and mined the 20th after restart. All three runs exited 0.

| Run | At 0 and 19 confirmations | At 20 after restart | Reservation and grant | Capacity check |
| --- | --- | --- | --- | --- |
| Stock | Committed | Committed, zero maker operations | Held, grant unconsumed and live | ACTIVE_LIMIT |
| Patched, unfunded | Committed | Cancelled, zero maker operations | Closed, unconsumed grant revoked | Slot available |
| Patched, durable record | Committed | Committed, prepared funding record retained despite unset funding flags | Held, grant unconsumed and live | ACTIVE_LIMIT |

After another maker restart, the unfunded control invalidated the actual refund block. Explicitly resuming the old swap kept it cancelled with zero maker operations. The capacity check used the production journal after clean shutdown with 127 synthetic active rows. The durable control seeded a prepared funding record to test retention. Bitcoin Core supplied the real BTC driver and chain clock. This run used seeded negotiation state and did not exercise BTC funding, a new proposal over peer transport, or a complete swap. The preceding coordinator run exercised fresh signed fixture proposals through admission.

Review found the terminal update, reservation release and grant revocation share one SQLite transaction. The transition requires a fresh exact canonical refund at policy depth and no local funding references, flags, durable operations, coin locks or consumed grant. A cancelled agreement skips recovery ticks and cannot accept a commit replay. Existing funded recovery is handled by the normal path and was exercised independently by the Python control.

The candidate build linked successfully. It initially failed to load an embedded Python module from the build directory. Running the identical binary from the task's virtual environment resolved the module lookup. Both binaries used SQLite wallets and embedded SwapNet. The stock binary had ZMQ enabled and was built with -Os. The candidate had ZMQ disabled and was built with -Oz. Probe setup pilots and build logs are retained. The nodes used private regtest directories and disposable wallets. Runtime ports and the local build booking were released. Nothing was published.

[Stock log](embedded-stock-final.log) · [Patched log](embedded-candidate-venv.log) · [Durable-record control](embedded-durable-control.log) · [Receipt](embedded-receipt.json).

Next step is a local two-peer run delivering a fresh proposal to the restarted maker with a dedicated Bitcoin regtest watch wallet. Publication remains on hold.

## Two-peer proposal after maker restart

Paired native macOS arm64 regtest runs exited 0 at #630 head `8d6d8b1a`. Both variants used the same compiled Bitcoin watch-wallet prerequisite from Session 2, separate disposable trading/watch wallets, two BTX daemons on loopback and one Bitcoin Core 30.4.0 regtest node. The maker capacity patch was the only difference between the variants. The old committed agreement and 127 other active slots were fixture rows. The old BTX refund was real regtest chain activity. The fresh RFQ, quote, proposal, agreement and commit went through the native peer connection.

- With the capacity fix, the old swap cancelled at 20 confirmations after restart. The maker started with 127 active slots and accepted the fresh proposal on its first delivery. Both peers persisted the same new agreement at `committed`.
- Without the capacity fix, the old swap remained committed at the same depth. At 128 active slots the maker received the proposal on the wire, recorded a packet error and created no new swap. The taker stayed `proposed`. Removing one synthetic row while the maker was stopped caused the **same** proposal to succeed on its second delivery after restart. The prior embedded journal check separately verified the `ACTIVE_LIMIT` error code.
- Read-only journal inspection after clean shutdown confirmed the acknowledged proposal and the matching committed agreement on both sides. The fresh agreement had zero funding or settlement operations on either side at shutdown. This test ends at admission and commitment.

All local processes stopped, disposable runtimes were removed after checking the log archives, and execution resources were released. No post was made. [Patched log](wire-patched-run1.log) · [Control log](wire-stock-run1.log) · [Receipt](wire-receipt.json).

Next step is a local final patch and evidence review for a concise handoff. Publication remains held.

## Final local patch review

Rechecked #630 open at `8d6d8b1aabf371b12f2b1f5797b950fed7962d4e`. The three baseline production files matched pinned upstream byte for byte. The four-file patch applied to the isolated review tree. Its three production outputs matched the frozen package inputs used in the patched two-peer run. Recomputed every hash in the candidate, embedded and wire receipts and checked the compressed logs. The reapplied patch passed all 120 SwapNet Python tests. The five focused tests on baseline had two expected failures and three passes. One reproduced the stuck slot and the other confirmed baseline never entered the new transactional cancellation path.

Reviewed the caller and transaction boundaries. The embedded worker serializes ticks, RPC and peer dispatch. The coordinator uses the local exact, canonical and fresh refund observation at the configured UTXO depth. The journal rechecks the revision, reservation and durable local funding signals before writing. It leaves funded recovery on its existing path. The store refactor preserves the existing settlement validation and audit sequence. The native run covers the BTX long leg with Bitcoin Core providing the short-leg driver. Reverse-direction BTC refunds, production rollout and the separate Bitcoin-RPC-outage patch combined with this one remain outside this run.

[Local handoff draft](HANDOFF-630-MAKER-SLOT.md) · [Final review receipt](final-review/receipt.json). All work remained in Session 3. Next action is to refresh the PR head and verify the selected attachment hashes if publication is explicitly authorized.
