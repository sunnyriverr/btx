# Scoped Bitcoin recovery verification of #630

Verdict: current3b0175dff3e377e5954d26dbc389b8dc9b0b7084 adopts the original Bitcoin payment after an older committed-stage restore, makes zero new funding attempts and retains a working refund. Native macOS arm64 Bitcoin Core30.4, Python3.11; current production coordinator, UTXODriver, Journal and encrypted export/restore, with a simulated BTX counterleg. AI assisted preparation and testing.

## Results

| Target | Observation |
| --- | --- |
| cb823a94 baseline | Old committed backup, original coordinator stopped before restore, wallet/chain retained: two distinct confirmed10000sat contract outputs, disjoint funding inputs,330sat fee each. |
| 3b0175df current | Same restore stage adopts original outpoint; zero additional wallet funding attempts. Early refund rejected. After maturity, refund spends original output and pays agreed beneficiary9900sat with100sat fee. Two confirmations and coordinator reopen preserve refunded. |

The candidate's existing payment was in the native mempool at adoption. Its refund subsequently confirmed. Two confirmations are an explicit test policy, not the default finality profile. Current fresh-funding on Core30.4 rejects the new psbt_version option. Fixture setup ONLY omits that option to create the original default-v0 payment. Restore uses a newly constructed UNMODIFIED current driver. Attempt counters run before wallet RPC dispatch. No such option is suppressed on the recovery path. Core32.1 not tested.

This confirms the supplied Bitcoin recovery change in the scoped path. It does not qualify embedded BTX/P2P settlement, native BTX wallet coin selection, ETH, full crash recovery or a release. Prepared-snapshot control retains the original payment but remained waiting; that is not presented as full progress. Earlier ordinary restart control retained one payment.

## Evidence

current-observations.json records the exact outpoint, refund, output value, confirmations and counters. baseline-observations.json and baseline-funding-pilot.json retain the distinct accepted payments and controls. Witnesses/raw transaction bytes are omitted from public result JSON. native-receipt.json and current-native-receipt.json record original local file hashes and upstream module identities; some hashed raw logs remain local.

executed-current-probe.py and executed-baseline-probe.py are the exact executed scripts. Their retained-workspace Bitcoin executable path is historical context. reproduce.py is a portable adaptation of the current script, changing only that path to BITCOIND. It was syntax checked, not separately rerun. The reported result comes from the executed script. The baseline reused the already-created duplicate payments after correcting a mined-transaction lookup, rather than creating duplicate payments again.

## Reproduction recipe

Use a disposable machine without production wallets. Requires pre-existing Bitcoin Core30.4, Python3.11, pytest and cryptography. Check ports38641/38642 are unused and leave1.25GiB free. The script asserts Bitcoin regtest genesis, creates disposable wallets under its own directory, mines test blocks and stops its node. Do not point it at existing chain data.

From an exact3b0175df checkout plus this evidence directory:

```sh
export BITCOIND=/absolute/path/to/bitcoin-30.4/bin/bitcoind
export PYTHONPATH="$PWD/contrib/swapnet:$PWD/contrib/swapnet/tests"
PYTHONDONTWRITEBYTECODE=1 python3 doc/review-evidence/bitcoin-restore-630/reproduce.py
```

Expected result is PASS_ADOPTION_AND_NATIVE_REFUND in current-native-result.json. The runtime directory must be new. No product patch or additional financial-policy proposal is included. Credits: repch1c's original old-bundle report and Numair's supplied adoption implementation.
