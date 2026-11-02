# Native Atlas mixed arguments: pass; sole macOS CLI URI: missing

Exact Atlas target `acbf7efb20b1b82da06affdae2ead08068cf743c`. One native macOS M4 sequence, same retained isolated executable throughout. This addresses Numair’s #273 comment6570878019 item2, plus controls.

- A real second process passed a URI and a .btx path to the already-connected first process. Both distinct preview values appeared, one each. Closing the top file preview exposed the URI preview; closing that exposed the workspace. Three later advancing ordinary footer observations showed no duplicate.
- A sole .btx file delivered correctly. A sole URI did not appear during52.8 seconds and three advancing footer observations. A subsequent distinct .btx file delivered a visible preview during ordinary polling (observed18.9s after launch), showing the app/dispatch/polling were still operational. A no-argument launch remained quiet for25 seconds.
- All five second processes exited0; first PID31792 survived each. No manual refresh or tab switching, direct queue injection, parsing, inference or spending was used. Backend RPC logs corroborate periodic reads; UI evidence is in ui-observations.json.
- The sole-URI issue already has a proposed platform guard in repch1c’s #286 commit89a8c8e9. Current #273 unconditionally skips a sole scheme argument; #286 limits plugin forwarding to Windows/Linux. This run confirms the current Mac symptom, not a tested ACK of #286. No duplicate fix was built.

## Reproduce
Use the isolated app binary identified in summary.json; connect it through its normal cookie confirmation to a disposable wallet-disabled loopback regtest node. With the first instance polling, invoke the same binary with a synthetic btx: URI plus a .btx file containing a distinct URI. Close previews without parsing them, count exact values, and observe subsequent ordinary footer timestamps. Repeat separately with a sole path, sole URI, recovery path and no arguments. launch_case.py records the exact invocations used here; its scratch path/PID are run-specific and must be replaced for a fresh run. lab.py records the node setup. Full app source/build identity is retained in atlas-downloads-native and parallel-work-20261102/test-readiness.

## Scope
HTML preview dialogs rendered in the native Tauri app, not native OS confirmation dialogs. Direct CLI second-instance delivery, not LaunchServices/default handlers. The retained backend is an older #280 test binary, only used for a live local connection at regtest height0; modelnet and wallet were disabled, peers0. User completed the initial local connection dialog because the app-control tool timed out on that modal. One bounded macOS run; no Windows/Linux, payment/address validity, release or #286-fixed runtime qualification. Inert synthetic addresses were never parsed. No claim that a finite observation excludes every future duplicate.

## Next decision
One concise scoped handoff can close #273’s mixed-argument Mac check and point out that #286’s Mac sole-URI guard is still absent from this target. Prefer adoption/testing of the existing fix over a new patch. Nothing published by this run.
