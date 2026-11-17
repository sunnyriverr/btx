# Independent native historical-fee qualification audit

**Verdict: the selected technical acceptance is satisfied at the stated native RPC/fee boundary. No repair, repeated passing run or broader qualification is required.** Read PLAN.md, run_native.py, result.json, source-receipt.json, qualification-receipt.json, the archived preflight result and admission/native-fee-source-preflight.json; reviewed the relevant current helper and read-only local Git source comparison. No tests/product execution, code edits, network or publication by this reviewer. Only this report written.

## Identity and compatibility

The run asserts the saved actual daemon checksum ac96c05d6a83a09dbb902f0d89fd04049897a0ac659660c228926a1ed31b9e6f before startup and records native source949a98e34222cc4cdb5b1d5bd650aa3b7bcbff72. Loaded external Python drivers/rpcclient paths and hashes match source-receipt.json's currentbd847e2b986722c1723b4cd60988d4f4908452d4 selection. The helper is current adopted806 code, not the package's old embedded coordinator.

Admission records byte-identical949/3710 rawtransaction.cpp and core_write.cpp hashes. The exact local Git3710→bd847 diff for those files is empty. This establishes the relevant native fee response/serialization source compatibility for the selected old binary, not equivalence of every current daemon dependency, native build or release profile. Neither source compatibility nor a passing helper upgrades the saved package to a current binary claim.

## Successful observation and refusal controls

The harness uses the copied retained chain/wallet checkpoint and original published transaction c74afd1103b34492cf94f67e4add65edf525744fe2dbb8bb0bf3b4826710c1ea. It verifies SHA256 of the decoded original transaction bytes against the prior receipt, checks native decoded txid, selects the existing100000-atom output, and supplies its exact script/index/amount and native asset/genesis to the production reader.

Production historical_funding_fee returns7834 atoms from the actual native getrawtransaction verbosity2 response. Recorded calls show the wallet blockhash-hint/explicit-block path is exercised, including current canonical block-header checks and raw txid validation. The oracle is the separately obtained native wallet gettransaction fee, negated and scaled only inside the harness. Its7834-atom agreement is a useful independent RPC representation check for this known locally sent payment; wallet fee is not passed into the production fee decision. Do not describe it as an independently audited chain-consensus calculation.

The wrong script is supplied against the same real transaction/reference and receives RECOVERY_CONFLICT. The known-absent synthetic txid triggers real native transaction/wallet lookup failure and yields FUNDING_FEE_UNKNOWN. This is genuine unavailable-transaction refusal; it is not observed pruned-undo/missing-undo behavior. The helper has no Journal/Vault/signing dependencies in this run, and no successful refund replacement is performed. Existing matched component cap/principal/maturity/retry/safe-refusal evidence is correctly reused for those distinct contracts.

## Bounded operation and cleanup

The instrumented RPC allowlist excludes mining, transaction construction/signing and broadcast. The existing wallet may be loaded on the disposable copy, which is a local runtime action rather than a new payment. Native height remains105, and no new funding/mining/signing operation is issued. The node is started with swapnet/modelnet disabled, peers/listening disabled, explicit old wallet-test MatMul/autoshield settings and a private copied datadir. This is not an entirely mutation-free filesystem operation: native startup/wallet loading/shutdown legitimately write the disposable copy.

result.json records clean process termination after stop. qualification-receipt.json records removed own runtime, unchanged original checkpoint and retained source/log/hash receipts. source-receipt.json preserves the original checkpoint inventory. This reviewer relied on those cleanup receipts rather than restarting the node or rehashing the wallet/chain as another product run. The parent should retain/release actual bookings consistently at closeout; no peer/production resource use is evidenced.

## Initial setup failure

The archived preflight result failed before any getrawtransaction fee query: its call list ends after original wallet gettransaction and stop. The corrected harness hashes bytes.fromhex(entry['hex']) rather than UTF-8 hexadecimal text, matching the prior raw-byte hash contract. Keeping the failed setup receipt separate and correcting once is appropriate; it does not count as a product failure or a second passing qualification. The archived initial native_source string is malformed metadata and must not override the correct full source/checksum in the final passing result/receipt.

## Scope and completion contract

The current helper is qualified against a real source-compatible archived BTX node for an ordinary timelocked P2MR payment's historical total fee and output binding, plus actual unknown lookup refusal. The supplied terms are a thin object bound to that ordinary output; they are not an authenticated SwapNet agreement/HTLC. There is no actual shielded funding, native currentbd847 binary, default MatMul, embedded worker, full Host restart, bilateral SwapNet, HTLC refund replacement, public-chain/release, or pruned-undo qualification. Those exclusions are explicit and do not block this finite plan.

**No selected technical acceptance remains missing.** The goal can finish once its already-required administrative closeout is complete: concise report/qualification limits, task/owner/queue/wiki consistency, actual resource release and final user-facing no-fix result. No post/push was authorized or required. Do not leave the goal active to create another task, seek acknowledgement or fill a native matrix cell. Adoption/release assurance remains distinct from this completed local integration result.
