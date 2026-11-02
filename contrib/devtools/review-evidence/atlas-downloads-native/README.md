# Native Atlas Downloads acceptance at acbf7efb

**PASS for #273 item 4: the native Downloads row updated after a real transfer without another tab click.**

Requested by Numair in [6570878019](https://github.com/btxchain/btx/pull/273#issuecomment-6570878019).
Tested Atlas revision: `acbf7efb20b1b82da06affdae2ead08068cf743c`.
One run on 2 November 2026, macOS 26.5.1 (25F80), Apple M4/arm64.
Testing and evidence: Sunny River, AI-assisted. Fix: Numair's upstream revision;
this branch adds evidence only and changes no product code.

## Result

Downloads was selected before starting a real FREE_ONLY loopback PQ1 acquisition.
The job was started through local node RPC, not Atlas's write form. Only the
owned seed process was paused for about 26 seconds to make the pending state
observable, then resumed. The same native row changed from `downloading` to
`retrieved / local / 100`, with no intervening tab click, navigation or manual
refresh. UI evidence is from the actual Tauri/WebKit window, not a browser mock
or an injected Store update. The pending percent displayed a dash, not zero.

| Observation | UTC |
|---|---|
| Job started | 07:37:05.294 |
| Native downloading row captured | 07:37:19.456 |
| Seed resumed | 07:37:31.245 |
| Backend first observed done | 07:37:31.757 |
| Native local / 100 captured | 07:37:42.753 |

The completed UI footer observed 07:37:41 UTC; the screenshot subsequently shows
07:37:51 UTC. These are sampled observations, not an exact repaint-latency benchmark.
Job ID `5670a205b85ea3ac1cf2fb6e0e6878ba` matches UI and backend records.

After the positive observation was saved, Shared retained its own columns/actions
while footer observations advanced from 07:38:32 to 07:38:52 UTC. Downloads did
not replace that table. Returning to Downloads retained local / 100.

## Byte verification

The synthetic SafeTensors artifact was 9,437,264 bytes, transferred in three pieces
(4,194,304 + 4,194,304 + 1,048,656). Reassembly in numeric order matched both the
original file and received manifest's SHA-384:

`5c9461f3eccfeace0b3496017f47037812924773b1356f08ad28a69861388c9e9e54f46aec1c96f52520ee375b242f70`

Backend: job `done`, bytes_committed 9,437,264, state `local`, percent 100,
complete=true, incomplete=false, bytes_verified=true. The intentionally paused seed
caused two peer retries. Automatic spend and paid atoms stayed zero. The buyer's
structure_verified=false is preserved: no inference/model-admission claim.

## Build and scope

Atlas product sources were unchanged. Rust 1.95, offline locked release build,
one compiler job, same committed Cargo.lock. Build-time TAURI_CONFIG overrides
only the identifier to dev.btx.atlas.downloadstest, isolating existing app data.
Local unsigned app wrapper, not an installer. Native binary SHA-256:

`df4f93614300fcd240169c930eb6835c201f3435a4395ae9bd45010ef8296e5c`

The backend uses retained, hash-verified older binaries: helper at baseline
cbf65894 and node from the #280/65fa2abb test context. Full binary hashes are in
backend-identity.json. This is a controlled frontend acceptance check, not an
all-acbf backend build or whole-PR approval.

One native macOS transfer; no Linux/Windows desktop, WAN performance, wallet funds,
inference, mainnet, production admission, signed installer or release qualification.
The user approved the connection modal manually when automation could not read it;
the native acquisition approval flow was not tested. All model peers were loopback,
external discovery/seeds disabled, node at regtest height zero with wallet disabled.
Owned app/services were stopped and disposable credentials/data removed afterward.

Our [earlier native failure at6d0fbf6b](https://github.com/btxchain/btx/pull/273#issuecomment-6549450194)
is historical evidence; it was not rerun here. Do not describe this as a new
identical-harness before/after matrix. The specific reported refresh failure was
absent in this run, supplying the requested native acceptance evidence for item4.

## Evidence and reproducibility

- `ui-running.txt`, `ui-after-resume.txt`, `ui-completed.png`: native result.
- `ui-shared-*.txt`, `ui-returned.txt`: tab controls after completion.
- `backend-observations.json`, `buyer-manifest.json`, `fixture.json`, `summary.json`:
  matching job, transfer and byte identities.
- `native-identity.json`, `backend-identity.json`, `source-identity.json`,
  `build.log`, `build-result.json`: exact inputs, hashes and build result.
- `REPRODUCE.md`, `lab.py`: manual native sequence and original loopback lab launcher.
  Set binary paths to your own matching builds; no UI script bypasses OS approval.
- `SHA256SUMS.json`: published file integrity.

The summary's no_post=true records the original private capture state, not an
ongoing restriction on this subsequently authorized evidence publication.

Setup notes: initial Python archive extraction and a copied lab path failed before
runtime and were corrected. The first dependency build was interrupted to add the
isolated application identifier, then completed normally. A recorder initially
checked status at the response envelope instead of jobs[0], so it unnecessarily
continued 60 polls and printed 'Not terminal yet'. Raw records show done in the
second sample; verification uses jobs[0] and the matching byte count. No second
transfer or excluded failed product run was hidden by that recorder mistake.
