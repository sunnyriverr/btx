# Funded BTX-to-Bitcoin lifecycle: PASS

Native Ubuntu24.04 x86_64 job43576084156 reuses saved candidate772b35d27a72a457f3995beea5597310a0b7a521, without compilation or another discovery run. Bitcoin Core30.4 checksum/binary identity and all saved payload checksums verified. Result artifact14106249018 downloaded and SHA25626c5d3c28b5b1b2460d74a2dc9e76004f6798a8b3888a6774b64c2b1a5dbe1a3 matched. Reused Session2 recovery/settle.py, with previously passed wallet-refusal cases removed and strict terminal-state/reopen assertions added.

## Settlement after funded restart

Both BTX nodes stopped after the original BTX payment had one confirmation. Restart retained the original outpoint and one funding operation. Both sides later reached complete. Direct transaction inspection verified HTLC input/output commitments, claim destinations and each fee; all four wallet deltas matched expected chain payments. BTX locked20000000atoms, paid19991000, funding fee7834, claim fee9000. Bitcoin locked39990000satoshis, paid39989560, funding fee330, claim fee440. Watch/signing wallet isolation passed. The exact long-leg funding script appeared once on chain. Restarting both terminal nodes retained complete and identical operation records.

Fixture assistance: Bitcoin peer lagged at140while miner reached160; inherited helper submitted canonical blocks141–160 to the lagging peer and verified hashes. This qualifies settlement against validated chain state, not uninterrupted automatic external-chain relay.

## Mature refund after restart

Separate fixture funded the original BTX long leg once, then restarted the initiator while maker stayed stopped. Early refund refused at133; original output remained unspent before contractual maturity2212. Saved refund appeared at2212, spent that original outpoint, returned19991000atoms to the original owner, and confirmed20times. Funding fee7834plus refund fee9000matched wallet loss16834; Bitcoin balances unchanged. One funding, one refund, no claim/secret exposure. State reached refunded and survived terminal restart with identical operations. Both cases cleanly stopped owned processes, cleanup_errors empty.

## Limits and next decision

This is native Linux BTX→BTC on Core30.4, ModelNetOFF, disposable toy-regtest MatMul activation settings. Reverse BTC→BTX and full Core32.1 native settlement are open; ETH/platform/release gates remain. No new interrupted-accounting or Bitcoin-RPC outage fault was injected. Prior scoped fault tests remain separately attributed.

The tested repair/build/discovery/lifecycle package now supports one consolidated #630 handoff with exact limits. Prepare it locally; publication hold remains. Broader reverse-direction qualification must have its own scoped acceptance row rather than being implied by this pass.
