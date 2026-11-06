# P2MR supplied-parent PSBT regression

**Tested PASS on unchanged `666673a3`: both public update routes supply a previously unknown parent, after which the intended wallet signs and finalizes the child.** The same case is proposed in code commit `e2ad728a911b948d6814951eb64858df0dd14af0`, tree `b1541ba8cba6013f4f6228bc02fa1fef1a60e104`, with one default BTX-matrix registration. This adds coverage for working behavior, rather than a wallet bug-fix before/after claim.

## Why this case

The generic `rpc_psbt.py` returns after its P2MR smoke before the supplied-parent checks. Dedicated multiparty and HTLC cases exercise different paths. This case independently starts both routes from the same bare child and uses the current `descriptorprocesspsbt` options object. Existing generic supplied-parent checks and the maintained multiparty wallet setup informed it; source licenses are retained. Repch1c's [coverage clarification on #410](https://github.com/btxchain/btx/pull/410#issuecomment-6658724698) helped distinguish those skipped checks from the tested HTLC work.

## Observed result

One 8-second native execution in [run42146725797](https://github.com/sunnyriverr/btx/actions/runs/42146725797):

- A genuine funded/signed parent passes mempool acceptance but stays absent from mempool, UTXO view, enabled txindex and both wallets during all offline checks.
- Bare, missing-parent and unrelated real-coinbase-parent controls remain incomplete without spent-output data.
- Both `utxoupdatepsbt` and `descriptorprocesspsbt(child, [], {"prevtxs": [...]})` populate the exact spent output without changing the unsigned child. Descriptor processing has no keys and remains incomplete; the recipient wallet signs, then finalization extracts the expected transaction.
- Only afterward is the parent deliberately relayed. The child passes mempool validation; both confirm in one block. Normal node stop completes, no fallback signal or owned node/CLI survivor remains, and the runtime is removed.

See [test log](supplied-parent-psbt.log), [native result and commands](native-result.json), [artifact/source verification](native-verification.json), [complete build log](root-build.log) and [source mapping](source-map.json).

## Executed build and entry point

Ubuntu24.04 x86_64, GCC13.3, Release/O1/NDEBUG, CMake3.31.6, hash-pinned OpenSSL3.5.9. The maintained root `btxd` and `btx-cli` targets built with wallet and Modelnet **compiled ON**. The testcase runs Modelnet OFF, txindex ON, with the existing wallet-only regtest MatMul-height knobs from `wallet_p2mr_multiparty_psbt.py`. Its setup uses the Modelnet command-line switches available in that declared build profile. **WITH_MODELNET=OFF builds were not qualified.**

Actually executed fixture: `e3448966863a11539e743b9925a83915235740d5` ([workflow](https://github.com/sunnyriverr/btx/blob/e3448966863a11539e743b9925a83915235740d5/.github/workflows/p2mr-parent.yml), [runner](https://github.com/sunnyriverr/btx/blob/e3448966863a11539e743b9925a83915235740d5/contrib/devtools/p2mr-parent/run.py)). Identical copies are here as `workflow.yml` and `run.py`. It checks out exact product `666673a3153225ba264c7870e0e82e354df86765`, builds the targets, invokes the case with explicit config/fresh directories and verifies cleanup.

The exact executed argument vector is the `supplied-parent-psbt` command in `native-result.json`. PYTHONPATH points to that product's `test/functional`, and BTX_OPENSSL to the pinned prefix. Testcase SHA256: `8341a31754471e79851468db0cc18788f8507c9388046f6dc78f9e060b7c69cd`. The proposed in-tree file is byte-identical to this executed external-path fixture.

An equivalent **in-tree invocation**, provided for reviewer use rather than claimed as another execution:

```sh
PYTHONPATH="$SRC/test/functional" BTX_OPENSSL="$SSL/bin/openssl" \
python3 "$SRC/test/functional/wallet_p2mr_external_parent.py" \
  --configfile="$BUILD/test/config.ini" --descriptors \
  --tmpdir="$FRESH_CASE_DIR" --cachedir="$FRESH_CACHE_DIR" --portseed=41931
```

Use the declared wallet+Modelnet-enabled profile and new disposable directories. The proposed registration is in `BTX_BASE_SCRIPTS` with `--descriptors`, appearing once in the deduplicated extended/explicit union. Registration was source/AST checked; the full `test_runner.py` dispatch or matrix was not executed. Direct native invocation used the same descriptor-mode default.

## Identities and limits

- btxd SHA256 `4ad63b64f6d6bab34f5ba92518dc8955ee2e263e0daa4d739f27ec868fce0ae1`; btx-cli `b71061e57a9224d86ef2f17da1914f3b68ffe91b696282151c0aba9e12caa5b8`.
- Four native catalogs compare all 14,309 tracked blobs/modes with immutable source before build, after build, after test and at finalization. Their shared SHA256 is `c8497991392e27c28ffe00a22284413fb2863f1b9474a4a191dc95a11e5be2e0`. Raw catalogs remain in the native artifact; its complete manifest and verified comparison results are preserved here.
- Artifact13472590446 SHA256 `559d3f09566bd1c0b87d79089e2d9678c30e633a01955875584e1389f2d737fa`, inspected in memory and hash checked; artifact expiry 2026-11-13. Essential commands/configuration/logs and this manifest remain in the evidence branch.
- Initial run42145374913 stopped during a redundant apt CMake download before compilation or node execution. The replacement uses installed CMake and bounded downloads. Product/test bytes did not change; this is setup recovery, not product fail-before/pass-after evidence. See `setup-attempt.json`.
- No full unit/functional suite, other build configurations, Mac/Windows, default MatMul/device admission, live-network, restart/persistence or release qualification. Actual node RPC handlers were exercised; command-line argument conversion was not. Runtime product code and consensus rules are unchanged.

The CI result omits generic runner telemetry (hostname, memory and disk observations). The verification record omits local collection/storage telemetry. `manifest.json` gives hashes for the exact published bytes and any ANSI-only log transformations.
