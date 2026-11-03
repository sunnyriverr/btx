# Native macOS sendheaders fixture evidence

The test-only commit is identified in identity.json. REPORT.md states the scenario changes, failed pilots, measured outcomes and limits. paired-run.json is the checked final collection; summary.json also records the earlier complete pass whose collector failed after automatic cleanup. Logs here retain test/node events with the personal workspace/home prefixes replaced by `<workspace>`; they are not the unredacted byte-identical private logs.

## Reproduce on a supported local build

Use a full checkout of this branch and your matching build's generated test config. The exact final test file is the native entry point:

```sh
BTXD=/absolute/path/to/btxd BTXCLI=/absolute/path/to/btx-cli python3 test/functional/p2p_sendheaders.py --configfile=/absolute/path/to/build/test/config.ini --tmpdir=/absolute/path/to/new-owned-scratch --nocleanup --timeout-factor=1
```

Use a fresh owned scratch path. The recorded run used a wallet-disabled build/config and the retained identified binary; no clean rebuild or run on your platform is implied. Expect the fresh proactive proof, Parts1–5 success and final Tests successful. Repeating with only the `self.isolate_ordinary_announcements()` call replaced by `self.ordinary_relay_ceiling = 0x7fffffff` produces the original Part1.0 exact INV assertion failure. Do not change production relay policy to obtain the control.

This was a local authorized disposable-node test. No production data or real wallets were used. Source and evidence were prepared with AI assistance and internally reviewed; independent human/native Linux/Windows verification remains separate.
