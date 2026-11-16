# #774 P2MR payment qualification — actual result

The corrected approved Ubuntu24.04 x86_64 run43862996861 established the missing ordinary-payment regression. Retained1e2baseline verified; JPP774exact3-file delta applied; candidate btxd built successfully with normal dependencies/GCC13.3.0. Both binaries used the identical reviewed corrected fixture, fixed fee rate2atoms/vB,100count/1024kVB policy and existing CPU regtest profile.

| Outcome | Baseline1e2 | Baseline + JPP774 |
|---|---|---|
|100-ancestor self-spend chain remains unconfirmed|PASS|PASS|
|Independent confirmed0.7BTX coin available|PASS|PASS|
|Ordinary0.65BTX payment with avoid_reuse/APS|FAIL RPC-6, misleading long-chain refusal|PASS, mempool accepted|
|Final input/amount/change/fee/old-chain oracle|Not reached after refusal|PASS|
|Owned process group absent/scratch removed|PASS|PASS|

Each chain was387300vbytes, well inside1024000limit. The long-chain output held0.292252BTX; the independently confirmed input held0.7BTX. Baseline error: 'Unconfirmed UTXOs are available, but spending them creates a chain of transactions that will be rejected by the mempool'. The candidate uses only the confirmed input, pays exactly0.65BTX, returns change owned by aps, and pays0.00007834BTX fee. Its payment is in the regtest mempool and leaves the long-chain output unspent. No separate mining/confirmation of the final payment was tested.

This adds end-to-end P2MR payment coverage to JPP's existing Linux unit proof. It does not introduce another product fix. Credit Jpp-matata and Bitcoin Core PR36284. No unit suite was rerun; JPP's reported unit result remains separately attributed.

One matched baseline/candidate pair. Different PRNG seeds/disposable addresses, same fixture hash/policy/amounts. Direct maintained functional framework, not full functional test_runner integration or whole-suite qualification. No Mac/Windows, alternate signing-leaf matrix, production timing or real-funds claim. No additional repeated test is needed without a specific remaining uncertainty.

The initial approved43862116688 build passed but its fixture failed setup on an unindexed confirmed transaction lookup. No chain/payment result from that attempt. Corrected attempt uses wallet listunspent/gettransaction for outpoint lookup; no payment oracle or product source changed. Initial records are preserved. Candidate binary itself is not uploaded; exact binary SHA256 recorded alongside source/build provenance and logs.

## Evidence

Corrected artifact14223434009 SHA2568ebaa89b7270f5b26d7b983b3dc262b98593704ff5498f70f69ecd285492ba89 verified on download. See paired-verification-receipt.json, ubuntu-proposal/corrected-records/paired-results.json, both functional logs, candidate-build.log, preparation.json and verification-result.json. Baseline btxd9b9ba0f8...28583; candidate2bf7b6a9...5d6f0; CLI unchanged5f0b5907...9327d. Full hashes in receipt. Corrected fixture5e323a5e...6ddbd; full hash in receipt.

Fork workflow/records were authorized; no upstream PR/comment posted. No real wallet files or keys accessed. Both disposable process groups absent and scratch removed; execution ref/product-component bookings released after record. Task/fixture ownership retained for local final review/handoff. Peer SwapNet/ModelNet work independent.

Next: final source/evidence review, add the focused test's normal-runner registration if warranted under a fresh component booking, and prepare one short handoff for JPP on his existing774. Keep it local until publication is authorized. No new build or test required merely for a handoff.
