# Native Windows guard startup: tested fix 813d5629

Both startup blockers reproduce3/3 on `dac9aee53520bd49ed320ec7a49b9072fc7d88d9` and pass3/3 with `813d562929742636a36e34fe40ddfd0c8d712819`. The real node owns a READY guard on both boots and remains healthy after a clean restart.

- Windows Server2025x64, clang-cl20.1.8/MSVC14.51.36231, static CRT/OpenSSL3.5.4; Modelnet/wallet/tests/ZMQ compiled ON, GUI OFF. Runtime nodes are offline wallet-disabled regtest nodes at genesis.
- Bare supervisor startup fails before because the guard emits CRLF and the parent removes only LF. Fresh CLI store inspect independently fails before with SEC_PRIVATE_DIRECTORY because elevated-token creation defaults to Administrators ownership.
- The maintained native IPC regression passes23checks on each of three candidate runs, including private create/replace/read, broad file/directory ACL refusal, canonical/schema and large-request refusal, concurrent exchanges, stop/reap/restart and legacy no-authority checks. Existing validation remains unchanged.
- Real node: two boots,20health polls, one node-owned READY guard per boot, new guard PID/boot ID after restart, valid journal and automatic spend0. Both exits0; no forced cleanup or remaining children. Source code is limited to two product files and the maintained regression.

## Exact executed evidence

[Candidate run42711764629](https://github.com/sunnyriverr/btx/actions/runs/42711764629), [baseline run42710649995](https://github.com/sunnyriverr/btx/actions/runs/42710649995). Binary identities/archive hashes are in [manifest.json](manifest.json); [node lifecycle](node-lifecycle.json) and [before/after logs](logs) are directly inspectable. Full raw artifacts are attached to those runs.

The executed controller is [repair.py at3a21bf4c](https://github.com/sunnyriverr/btx/blob/3a21bf4ca6495f6a28658153b52644749bf2ca51/contrib/devtools/windows-root-configure/repair.py); its adjacent workflow/support files pin the profile, verify source/binary/cache hashes, build, execute and clean up. [Build commands](build-commands.json) are copied from that actual run. This is retained-cache CI, not a claim that a new clean standalone recipe was executed. The component driver uses the maintained IPC test and the actual root-built btx-guardd.exe; the standalone auxiliary guard target lacks ws2_32, so it was not used.

A first setup pilot42708783540 stopped at that auxiliary-target link. Baseline run42710649995 reproduced both bugs, then stopped at Git-bundle packaging before product compilation. The named-ref bundle command was smoke-tested locally; the successful candidate run reused verified baseline results instead of rerunning them. The actual incremental root build compiled five C++ objects and relinked nine executables in32.24s; original cache10223164157 was preserved.

## Limits

Full test_btx execution remains incomplete. No POSIX runtime, mainnet, production wallet, model worker execution/confinement, or release qualification is claimed. Existing incorrectly owned stores still fail closed; no automatic ownership migration is attempted. The separate Windows helper availability limitation is unchanged. This fixes new-store guard startup and subsequent node restart, not the entire #356 gate.
