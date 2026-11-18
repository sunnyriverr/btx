# Scoped native public-market result — a97af7b3

**PASS: native public BTX→BTC settlement/restart and original-payment refund on macOS 26.5.1 ARM64, using clean `a97af7b3f379e33e3ec65db948468d875ade2841` and Bitcoin Core 32.1.** This fills the native-peer public entry gap; it does not qualify default startup or a release.

| Case | Time | Observed result |
| --- | ---: | --- |
| Public offer → addressed quote → preview → owner confirmation → funded restart → settlement → terminal restart | 51.232s |PASS|
| Same public entry → original BTX funding → counterparty offline → recovery restart → maturity refund → terminal restart | 165.009s |PASS|

One execution each, zero skips, exit 0, no bound/cleanup errors; owned process groups absent. [Restart result](results/restart.json) · [Refund result](results/refund.json) · [Controller receipts](receipts) · [Exact provenance and limits](provenance.json).

## What was proved

Fresh disposable regtest nodes/wallets, actual native signing, transactions and chain observations. No seeded quotes or simulated chain/financial drivers. The maker's signed one-slot firm offer arrived through admitted native BTX peers; taker used `requestpublicswapquote`, nonfunding `previewswap`, and explicit `confirmswap`, all in the same `trader` wallet. Before confirmation: no taker mandate/session/coin lock, balance change or mempool change. Confirmation creates one bounded one-shot mandate; retries before/after funded restart reuse one original swap/payment. Maker slot moves available→quoted→reserved once. All50 original funded-fixture run assertions were retained.

Settlement checked original HTLC outpoints, locking scripts, recipient ownership and fee limits on both chains, plus all four wallet deltas. Atom deltas: BTX taker −20,007,834, BTX maker +19,991,000; BTC taker +39,989,560, BTC maker −39,990,330. Funding/claim fees: BTX 7,834/9,000, BTC 330/440. Completion observations20 BTX/26 BTC satisfy unchanged 20/6 confirmation policy. Terminal restart preserves operations and zero-held mandate accounting.

Refund: early refusal at initial 133 and maturity−1 (2225), original refund first in mempool at contractual 2226, raw refund 20 confirmations, same original input/owner destination, 19,991,000 atoms returned and exact owner loss 16,834 atoms. Both BTC balances unchanged; counterparty BTX remains offline and unfunded. Terminal `refunded`/operations/budget survive restart. The offline BTX maker balance was not queried afterward. The raw receipt records initial refusal 133; the maturity−1 assertion is in the unchanged fixture. Its 9-confirmation reported observation is an intermediate snapshot before the later terminal wait, not the final raw transaction check.

## Shared socket and diagnostic limits

**Shared control socket startup is NOT qualified.** Native logs report `shared control plane did not start (shared P2P socket path too long). Peer discovery continues.` The recorded fixture datadirs are too long for that socket. No switch/guard was relaxed to hide it. Native-peer discovery and the scoped SwapNet flows passed, but this is not acceptance of the separate shared control plane or whole-node default startup. [Restart excerpts](logs/restart-shared-control-excerpts.log) · [Refund excerpts](logs/refund-shared-control-excerpts.log).

Build/test profile: SQLite wallet ON; Metal, ModelNet, ZMQ, GUI and unit-test targets OFF; explicit serial CPU prover. Existing test-only MatMul activation heights deferred to 2147483647 and product-payload requirement disabled on disposable regtest only. Accelerated mock-time mining and neutral mining addresses; maturity is read from the actual agreement, bounded at 6,500 blocks, never reduced. `automatic_spend_atoms` stays 0. Saved Bitcoin Core HTTPS checksums matched; prior PGP verification was not performed. This is not default-consensus, mainnet, full-suite, GUI, EVM-finalized or release qualification. `finalized=false` in these UTXO observations is retained; exact source requires it only for EVM. The original canonical block-relay fallback was present but unused in both runs.

## Identities and reconstruction

[Successful clean node build](https://github.com/sunnyriverr/btx/actions/runs/44234401274): compiled in 628.039s with 2 jobs; clean source, no overlays. [Build result](build/result.json), [actual configuration](build/CMakeCache.txt), [checkpoint and binary verification](build/checkpoint-verification.json). The raw build field `compiled_bytes_unchanged` describes the pre-build preservation audit, not post-build object equality; inherited archive scope prose is superseded by exact successful build result/hashes. Post-build seven known build-info/clientversion/canary/restat-dependent edges were recorded without repeating the successful build.

Executed fixture and controller are byte-identical: [funded_public.py](fixture/funded_public.py), [run_prepared.py](fixture/run_prepared.py). Original commands were `python3 -B run_prepared.py --execute restart`, then `python3 -B run_prepared.py --execute refund` after PASS, from the local fixture directory. [Stage logs](logs) retain the actual sequences. Reuses our earlier native funded fixture and upstream public-RPC contracts; not a newly registered in-tree test.

For reconstruction, rename `fixture/manifest.example.json` to `manifest.json`, supply paths to the exact verified binaries and the qualified Python 3.12.10 framework (cryptography 46.0.4 / cffi 2.1.1 / pycparser 3.12), and run from the fixture directory on an isolated Mac. The example manifest has sanitized paths and **was not itself executed**. Choose short isolated paths if separately qualifying the shared socket; that setup remains unexecuted here. Each case hard-limited to 600s, with 1 GiB scratch and a 1.25 GiB free reserve; preserve failed runtime and stop at any refusal. No build, install or production wallet access in the controller. [Offline mocked controller checks](fixture/test_controller_preparation.py) verify result/interruption handling only; their 3 PASS cases are not native financial proof.

Wallets, cookies, private keys, raw runtime databases and personal paths are excluded. Public path substitutions and original/published hashes are listed in provenance; native result JSON and executed source are byte-identical. Test preparation/execution used AI assistance; internal review does not replace independent replication.
