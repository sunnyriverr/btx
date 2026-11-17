# Installed GUI fixture — source review only

Prepared from Session 2's runtime/run.py and ui.py recipe, whose historical acceptance run was 43499330842. Credit remains with Session 2 for that recipe. These new files have not been imported, syntax-checked, compiled or executed. No current Qt or Atlas runtime result is claimed.

## Exact source contract inspected

Read-only GitHub file reads at compiled source 074dac167c26c1e091198f691ed5727817dba88a:

- gui/atlas/web/app.js, Git blob 3b09ebef95ae929b41248647e159380f1cca0b6f: line 41 displays LIVE LOCAL and the observed chain/blocks; lines 51 and 54 define the welcome, connection and endpoint controls.
- gui/atlas/src-tauri/src/host.rs, Git blob 8e044bea76b72d83eb74d61f369658849126146f: line 227 defines the native cookie-picker title; line 242 defines native endpoint/chain/genesis confirmation.
- src/init.cpp, Git blob 55e11d82667c1398591e486b903efba966284b93: lines 653 and 886 register modelnet=0 and networkactive=0. Existing recipe already exercised wallet-disabled local regtest flags on its older source; the new fixture must establish current execution separately.

This candidate's producer explicitly reused an older Atlas input. The source audit explains the reviewed UI contract and current node flags; it does not claim a new Atlas build or qualify all current Atlas code. Parent input/provenance admission retains that distinction.

## Changed assertions and isolation

- Uses the single prefix installed by the controller. No separate extraction, dependency repair, build or alternate executable path.
- Uses a fresh private HOME/XDG tree, separate node and Qt regtest datadirs, loopback RPC, wallet disabled and node/model networking disabled. No real wallet, keys, coins or peer contacts.
- Qt must display a PID-owned regtest window and close normally with exit zero. Atlas must use its actual native picker and native endpoint/chain/genesis confirmation. Two separately captured observations must both contain LIVE LOCAL, regtest and 0 blocks while the app remains alive. There is no JS bridge/state injection.
- Window closing uses the exact child PID/window ID, avoiding a broad BTX title. Cleanup enumerates the unique installed prefix and newly created process sessions, including host WebKit descendants; each fallback target is rechecked against its PID/start time/executable record. Any fallback signal or remaining process fails the result. The pre-existing-process refusal cannot reach fallback cleanup because ownership is established only after admission.
- Records screenshot hashes, intended host GLib/DBus resolution, Atlas loaded mappings, actual executable paths and immutable installed file inventory. No cookie contents are read into records or passed in arguments. Runtime files are deleted only after no scoped process remains.
- Missing dependencies, ambiguous controls, app crashes, wrong chain, early close, changed package bytes and absent observations fail closed. The fixture does not install a library after failure.

## Limits / next gate

Future dedicated Ubuntu 24 X11 execution must establish that runner accessibility, app process/window ownership and normal WM close behavior still match these assumptions. Native dialogs are platform-dependent. Prepared screenshots will require visual review after a real run. Whole controller timeout is an independent failure, never a pass. No ModelNet transfer/inference, SwapNet operation, updater download/signature path, wallet payment, cross-distro portability or official release acceptance is covered.

Source review corrected two defects inherited from the old orchestration: the second connected observation now has explicit assertions, and cleanup refuses to signal a pre-existing process when startup admission fails. No runtime evidence was generated to verify those corrections.

Integration review added SIGTERM/SIGINT failure cleanup and atomic ownership records (leader PID/session/start ticks) for parent containment of host WebKit descendants even after a forced driver exit. Parent gives this driver100seconds cleanup grace and scans those sessions independently. These are source-reviewed changes only.
