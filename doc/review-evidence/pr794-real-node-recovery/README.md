# PR794: real outbound-peer recovery

Tested support for `4b882f8990fed1db7493cc7294defde5820b08ba`, extending repch1c's scripted-peer checks to two real btxd processes.

One matched native macOS arm64 / AppleClang17 run per variant, identical final fixture. The receiving connection is asserted outbound-full-relay with no NoBan permission. Both nodes generate and relay their own blocks; no test peer injects headers or bodies.

| Check | Only #794 production change removed | Candidate |
|---|---|---|
| Live announcement after receiver's 72-header cap drops ancestry | Original outbound peer disconnects | Peer retained; candidate's announced-body drop observed |
| Missing blocks / active tip | Recovery not reached before peer loss | All 93 branch bodies acquired; exact matching tips at 95 |
| Fresh progress | Not reached | Exact matching tips at 97 |
| Receiver restart, then more peer blocks | Not reached | Exact matching tips at 99; IBD false on both |

Recovery took approximately two minutes, following the existing GETHEADERS/probe window; it was not immediate. Raw [baseline](records/baseline-2.json), [candidate](records/candidate-5.json), [qualification](records/qualification.json) and compressed node logs in logs/ retain the observations.

## Identity and scope

- Candidate is the exact PR tree. Control changes only src/net_processing.cpp back to blob `65ba78031a7af832030cefed04cab6bc2184d782`, also the release `371013d6` network source. Other components are the PR tree, not a claimed clean latest-release integration. Binary identities are in records/.
- Mac MinSizeRel/g0, wallet, ModelNet and ZMQ disabled; Metal precompilation disabled. Matching Python3.12 library/stdlib supplied to the native executable. Maintained economic/cpu-diagnostic regtest defaults. No activation-height, validation, header-cap or parking override.
- Common ancestor at height 1, receiver branch of 6 and source branch of 93 blocks keep this case within default reorg policy and below MatMul activation at height 100, including restart and final height 99. This does **not** qualify MatMul-phase/GPU/attestation, the author's 20-block deep fork, WAN, Linux/Windows, full suite or a long soak. Health means the stated fresh blocks after restart.
- Author's flood, wrong-body and one-shot rejection controls were source-reviewed/reused, not independently rerun here.

## Fixture and reproduction recipe

The unchanged [executed fixture](fixture/p2p_pr794_real_nodes.py) has SHA256 `0aeb093b74cd6eb1e19d246dcbecb8d7ce033bebeeda41939343e93c7239254d`. From a clone containing candidate source and a matching configured node/CLI build, the portable reconstruction command is:

```sh
export BTX_PR794_SOURCE="$PWD"
export TEST_RUNNER_PORT_MIN=30000
# Supply the matching Python runtime library path/PYTHONHOME if required by your build.
python3 doc/review-evidence/pr794-real-node-recovery/fixture/p2p_pr794_real_nodes.py   --configfile="$PWD/build/test/config.ini" --portseed=794   --tmpdir=/absolute/new-private-regtest-dir --receipt=/absolute/result.json   --nocleanup --pilot-timeout=240 --require-pr794-path
```

The packaged-path recipe has not itself been rerun; original private-path launches are in records/baseline-2.log and candidate-5.log. Baseline fails on peer retention; candidate must also establish actual cap/missing-parent/body-drop reachability. Mere ordinary sync does not qualify.

## Pilots / provenance caveats

Earlier startup-library, activation at height 100 and 90-second-bound/Decimal-collector attempts were setup pilots, not qualifying runs. A manual-peer candidate/control pair both recovered: framework connect_nodes uses a MANUAL peer exempt from this punishment. The final fixture instead uses addconnection and asserts outbound-full-relay/noNoBan. Only baseline-2/candidate-5 supports this review. The baseline binary manifest's old fixture hash is labelled as the manual pilot; subsequent_runs and final-fixture-identity bind the actual final pair. Baseline's NON_REPRODUCTION label reflects absence of a candidate-only collector marker; raw cap/absent-parent/header-receipt/peer-loss evidence supplies the baseline failure.

Home/work paths are replaced with placeholders; source data hashes and transformed hashes are listed in records/redactions.json. No wallets, cookies, node configs, production data or compiled binaries are included. AI-assisted fixture/evidence preparation; executed observations and limits are recorded above.
