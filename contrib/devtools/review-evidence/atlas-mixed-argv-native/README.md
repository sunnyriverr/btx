# Native Mac Atlas second-instance acceptance

**acbf7efb: mixed URI + .btx delivery passes; sole command-line URI is missing on Mac.**

One sequence on Apple M4 / macOS26.5.1, replying to Numair's
[#273 item2 request](https://github.com/btxchain/btx/pull/273#issuecomment-6570878019).

| Case | Observed result |
| --- | --- |
| URI + distinct file contents | Both preview values once; close file then URI, workspace visible |
| Later ordinary polls | No duplicate at footer22:11:50,22:12:10,22:12:20 local |
| Sole .btx path | One correct preview |
| Sole URI | No preview for52.8s, with3 advancing footer observations |
| Valid file afterward | Correct preview observed18.9s after launch |
| No arguments | Quiet for25s |

All5 real second processes exit0, original process remains alive. Native UI
accessibility observations were extracted/transcribed into ui-observations.json;
they are not an instrumented event trace or independently captured video.
Every dialog was closed through its Close dialog button, without Parse locally.
No tab switching, manual refresh, JS injection or queue invocation was used.
Normal footer interval10s. Finite sampling does not prove absence of all future
duplicates. Actual observed ordering is file first, then URI; no ordering contract
is asserted.

## Existing fix, not a new finding

repch1c's open [#286](https://github.com/btxchain/btx/pull/286), commit89a8c8e9,
already adds a Windows/Linux guard for sole-URI plugin forwarding. The tested
acbf7efb callback skips that argument unconditionally. This result confirms the
Mac symptom on acbf7efb; it is not runtime approval of286 or proof of its fix.

## Reproduce

Build Atlas at acbf7efb20b1b82da06affdae2ead08068cf743c using its Cargo.lock.
The retained executable was built with Rust1.95, locked offline release build,
1compiler job, unchanged product sources and only a test identifier override
(dev.btx.atlas.downloadstest), in an unsigned isolated .app wrapper. Native binary
SHA256: df4f93614300fcd240169c930eb6835c201f3435a4395ae9bd45010ef8296e5c.
The prior build records are [committed here](https://github.com/sunnyriverr/btx/tree/72e7d6472a0e04fde027af53f9d03baf1efaae34/contrib/devtools/review-evidence/atlas-downloads-native).

Launch that isolated app with no arguments. Connect through its normal cookie
confirmation to a disposable wallet-disabled regtest node using:

```
btxd -regtest -datadir=<fresh-test-directory> -server=1 -rpcbind=127.0.0.1 -rpcallowip=127.0.0.1 -rpcport=<unused-port> -listen=0 -connect=0 -dnsseed=0 -discover=0 -natpmp=0 -disablewallet=1 -modelnet=0 -dbcache=32 -printtoconsole=1 -debug=rpc
```

Wait for LIVE LOCAL and advancing Observed footer timestamps. Establish no preview
is open. Use the same binary as the first instance for each actual second process:

```
python3 REPRODUCE.py /absolute/path/to/btx-atlas mixed --expected-sha256 <your-recorded-hash>
```

Record each exact textarea value by sequentially closing the top preview. After
both are closed, observe at least3 advancing ordinary footer timestamps without
refresh/navigation. Repeat separately with file, uri, recovery and none cases;
keep every first-instance dialog drained between cases. For uri, observe at least
3 advancing footer timestamps, then deliver recovery to prove the app remains
operational. Capture original PID/continued liveness and second-process exits.
REPRODUCE.py is a portable adaptation of the recorded invocations, not a rerun
performed for publication; launch JSON records preserve the actual invocation
sequence, timestamps, PIDs and exact fixture values used in this run.

## Scope and provenance

Native Tauri app and its HTML preview dialogs; direct command-line second-process
dispatch only. Not macOS system URL/file handler registration, cold launch,
resource parsing, address validity or payment execution. Synthetic inputs were
never parsed. Older retained backend from65fa2abb/#280 only supplies the live
local connection, at regtest0 with peers0 and wallet/modelnet disabled. No matching
acbf backend qualification. Backend SHA256:
03a3fb602e0a0dea77583f774ecf516f5875137829c2a9f6c03637f925300fc6.
User accepted the local connection dialog when app-control timed out on it.
No Windows/Linux, full-suite, installer or release qualification. Source/binary
identities, process results, UI evidence and selected method-only RPC log lines
are included. Original app/backend stopped and disposable test data removed.
Capture-time private/no-publication labels in records are historical; this
subsequent evidence publication is authorized. Detailed REPORT.md remains a
capture-time report. No product source is changed by this branch.
