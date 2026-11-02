# PR286 Mac sole-URI guard: native before/after

**The same sole-CLI-URI case fails on acbf7efb and passes with repch1c's 89a8c8e9 main.rs.**

One sequence/build, Apple M4 / macOS26.5.1 arm64. Baseline is Atlas at
acbf7efb20b1b82da06affdae2ead08068cf743c. Candidate changes ONLY
`gui/atlas/src-tauri/src/main.rs` to the exact file from
89a8c8e98a77934a02ff77dd71d0e52cfb2bf450. The product fix is repch1c's;
this evidence commit adds no product changes. Full PR286 head b7fe45c3,
including its Windows fileURL/ACL work, was not qualified.

| Input to actual second process | Baseline | Candidate |
|---|---|---|
| sole URI | absent through ~49s with advancing refreshes | exact preview once; quiet through later refreshes |
| distinct URI + .btx file | both exact values once | both exact values once |
| no arguments | quiet | quiet |
| sole .btx file | exact preview once | exact preview once |

All eight second processes exited0; original first instance survived each.
No duplicate observed during the recorded quiet windows. Those finite samples
are not a global exactly-once guarantee. Mixed inputs appeared file first, then
URI; no ordering requirement is asserted. UI observations were transcribed from
native CUA accessibility trees; raw AX files/video were not retained. Footer
timestamps are Brisbane local time; process launches are UTC.

## Reproduce the target

Use two isolated Atlas source/build directories at acbf7efb. In candidate only,
replace main.rs with the exact89a8c8e9 file (or apply guard-on-acbf.patch):

```
git show 89a8c8e98a77934a02ff77dd71d0e52cfb2bf450:gui/atlas/src-tauri/src/main.rs > gui/atlas/src-tauri/src/main.rs
```

This assumes89a8c8e9 is fetched into the clone. Source identities/hash manifests
are recorded in source-identity.json. Both builds use the same Cargo.lock,
Rust1.95.0 arm64, release profile, CARGO_INCREMENTAL=0, one job and isolated
target directories. We used the existing registry cache/offline build:

```
cd gui/atlas
TAURI_CONFIG='{"identifier":"dev.btx.atlas.downloadstest"}' cargo build --offline --locked --release -p btx-atlas -j 1
```

The candidate completed in226.4s. `build.capture.py`, build.log and
build-result.json capture the actual local recipe/output; sanitized path markers
are descriptive, not executable. Native wrappers are unsigned test .app copies
with the same identifier/Info.plist. Run variants sequentially, closing the first
before switching. Baseline binary SHA256:
df4f93614300fcd240169c930eb6835c201f3435a4395ae9bd45010ef8296e5c.
Candidate SHA256:
d9f172f041d52db5bcfc64638288ce73ff5657ae0de67b670bd819e8200e67b0.

Start a disposable backend with a fresh datadir/unused port:

```
btxd -regtest -datadir=<fresh-directory> -server=1 -rpcbind=127.0.0.1 -rpcallowip=127.0.0.1 -rpcport=<unused-port> -listen=0 -connect=0 -dnsseed=0 -discover=0 -natpmp=0 -disablewallet=1 -modelnet=0 -dbcache=32 -printtoconsole=1 -debug=rpc
```

The older retained65fa2abb/#280 backend supplied only connection/polling, at
height0/peers0; no matching-acbf node qualification. Its SHA256 is
03a3fb602e0a0dea77583f774ecf516f5875137829c2a9f6c03637f925300fc6.
Launch the chosen Atlas binary without args. Connect normally using that
backend's native-selected test cookie. The user accepted the confirmation when
app-control timed out. Wait for LIVE LOCAL and advancing footer timestamps;
keep the preview queue empty. Never use a production cookie.

```
python3 REPRODUCE.py /absolute/path/to/btx-atlas sole --expected-sha256 <recorded-hash> --first-pid <actual-running-pid>
```

REPRODUCE.py is a portable adaptation, not a rerun during publication. The eight
launch JSONs plus launch_case.capture.py record the actual executed harness.
Use the SAME first/second binary. Sequence: sole, mixed, none, file. Observe the
exact textarea values through normal polling, close each preview without Parse
locally, and record later advancing polls for duplicates. For baseline sole,
allow at least~49s with multiple advancing polls. Confirm mixed/file delivery
still works afterwards. Preserve the first process and check every secondary
exit. Drain mixed previews individually; observe at least30s of later polls.
Record noargs quiet and sole-file quiet windows of at least25s. Stop both test
apps/backend and remove only disposable data afterwards.

## Limits

Direct command-line second-instance preview delivery only. No LaunchServices
registration, cold-start, parsing/payment execution, Windows/Linux, installer,
full-suite, full PR286 or release qualification. Finite quiet observations;
one sequence per variant. Source/contract review in review/REPORT.md is internal
read-only review, not another runtime execution. Capture-time private labels in
records are historical; this evidence publication is user-authorized. Apps and
the disposable node exited, port closed, owned scratch removed. Production was
untouched. See REPORT.md, ui-observations.json and cleanup.json.
