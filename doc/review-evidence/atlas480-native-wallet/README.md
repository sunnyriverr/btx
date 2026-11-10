# Atlas #480: scoped native Linux wallet journey

**Tested ACK `f6b2ac8e606789d69c5d7a4edbf21ff11826b557` for this native journey.** JPP authored the #480 changes; this evidence supplements his existing DOM/demo coverage with an actual Tauri app and disposable wallet-enabled node.

## Result and limits

Ubuntu24 x86_64 virtual X11, real packaged native app, ordinary accessibility controls/keyboard. Regtest, explicit `-keypool=1`, zero blocks/peers/funds, Modelnet off. No WebView/bridge/state injection. One final baseline/candidate sequence, not a stability campaign.

| Check | Observed result |
|---|---|
| Baseline connection and wallet panel | Connected; repeat field absent; no wallet mutation. This is the first expected failure, not a claim that every later check failed before. |
| Candidate new-passphrase panel and operation form | Protected repeats and loss warning present; mismatches rejected in both forms; loaded/on-disk wallet sets unchanged. |
| Native cancellation | Exact createwallet method/name, regtest chain/genesis and redacted credential observed. Cancel returned CANCELLED and created no wallet. |
| Fresh explicit approval | Both secrets re-entered after cancellation; new native review approved once. Atlas returned `ok=true` and exact `result.name`; node independently contained that wallet. |
| Encrypted wallet | `descriptors=true`, `private_keys_enabled=true`, **present** `unlocked_until=0`; intended passphrase independently unlocked it through RPC, then it was relocked. |
| Legitimate controls | Existing-passphrase form asks once; secret JSON disabled; nonsecret JSON mode editable and reversible; palette Send opens Exact transaction composer. |
| Integrity and cleanup | All121 package files other than the replaced Atlas binary unchanged. Both apps/node exited cleanly; no signals/leftovers; owned runtime removed. |

Existing unlock is **UI field inspection plus independent RPC unlock/relock**, not execution of the native unlock operation. Nonsecret JSON was toggled/edited, not submitted. No payment preparation/signing/broadcast, default-keypool performance, macOS/Windows, hardware, full-suite or release qualification. Wallet selection used ordinary Wallet navigation after creation; automatic selector refresh is not claimed. Hidden raw-editor contents are source-reviewed, not asserted from its absence in accessibility output.

Endpoint was checked in connection approval. The operation confirmation shows method/wallet/chain/genesis/redacted parameters; it does not show endpoint. Captures below were visually inspected. Cookie contents, wallet databases, private keys and passphrases are not retained.

## Exact source and binary identities

- Candidate: [`f6b2ac8e`](https://github.com/btxchain/btx/commit/f6b2ac8e606789d69c5d7a4edbf21ff11826b557).
- Accepted node/baseline GUI: [`dac9aee5`](https://github.com/btxchain/btx/commit/dac9aee53520bd49ed320ec7a49b9072fc7d88d9). Baseline Atlas was retained from ff5f3f04 with the same accepted GUI subtree `a0bab679e2e6af917609f14b1c473e69a1fadcf4`.
- Reused package SHA256: `0caaa7d2d762d51bde262bff0bfb3965f58cc09bb1726b034783608930d3d633` (reconstructed desktop candidate, not an untouched official download).
- Baseline packaged Atlas: `a6765f554ecacfd32f80d2fc2f3a4d221fabd0ae18c47dd616ee5113d09d21df`.
- Fresh candidate producer: `b84d12beed2361927c81880735c177eb53a789f02482e39486f859b9c8e3ce02`; package-RPATH deployment: `b2b2d57fbc61207a1412aea8cb63bf86481648942b16957791eabec1ead30714`.
- Node: `bdd9273c2dcbf804a717e16bdcc4c08288f16c31cde59726f01924178487cb83`. No node/helper rebuild or modification was needed.

Six Cargo/native inputs were identical across base/candidate. Changed web assets required a fresh Atlas-only build: Ubuntu22, Rust1.95.0, locked dependencies, two workers,217.2s compile. Source stayed clean; binary GLIBC2.34/dependency inventory passed the existing2.38 ceiling. Original caches and working node were untouched. New build state was separately retained, but its restoration is unverified.

## Executed entry points and evidence

- [Atlas build run42773507615](https://github.com/sunnyriverr/btx/actions/runs/42773507615): `python3 contrib/devtools/atlas480-build/run.py`, exact workflow under [recipes/build](recipes/build/). Build/ABI records under [build](build/).
- [Native run42776427615](https://github.com/sunnyriverr/btx/actions/runs/42776427615), fixture `ac4a9890be5a6503d1a7f04076c96311a7e5ea59`: [executed native workflow](recipes/native/workflow.yml), [runner](recipes/native/run.py), [ordinary UI controls](recipes/native/ui.py), [classifier](recipes/native/result_handling.py). The workflow downloads the pinned retained artifacts, starts its own virtual desktop and executes the runner; it is not a one-file standalone reproduction.
- [Raw result](native/result.json), [execution/provenance receipt](provenance/execution.json), [artifact collection/hashes](provenance/final-collection.json), [file manifest](manifest.json). Native artifact13744077565 ZIP digest `2d196144ec347722ccab78ea568262e9f3ee1e15b7c009ba063e10224eccc58b`.
- [Baseline panel](native/baseline-panel.png), [native Cancel review](native/cancel.png), [native approval review](native/approve.png), [Send composer](native/send-composer.png).

The operation must return a successful UI result **and** produce the independently verified encrypted wallet. Node mutation alone does not qualify an UNKNOWN/lost response; approval is never repeated to resolve UNKNOWN. The saved response explicitly has `ok=true` and exact `result.name`. The classifier passed58 offline negative controls. `complete=false`/`LOCAL_NONATOMIC` in the response describes observation scope, not a release-wide guarantee.

Setup pilots are separate from the final result: build42772404590 stopped at apt transport before compilation; native42775126675 stopped at the test's cookie-location observation; native42775499968 reached the repeat checks but needed ordinary form scrolling. Fixture corrections reused the same binaries and wallet oracle. The first native pilot needed a fallback app signal; final cleanup required none. These are not extra passing wallet runs or product defects.

Next decision: whether this closes #480's scoped native Linux wallet-entry gap. Other platform and release decisions remain separate.
