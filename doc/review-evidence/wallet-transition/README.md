# Wallet transition evidence

Review entry point for one test-only PR targeting `btxchain/btx:release-0.34.17` at `1e2f8b5f12295002334d3390c12cac0bb4ae2aff`.

The exact test/runner bytes in code commit 8e924f975a7d0954a843bf603c784d6dca9eb8ec passed the normal framework in [run43808667522](https://github.com/sunnyriverr/btx/actions/runs/43808667522), CI envelope `995f7dd73002177ffd2fdf87304bc267f0ad799c`. One descriptors test and ALL Passed53s; zero selected skips. Wrapper80.61s; four post-assertion phase labels; process group absent and private data/old package removed. The clean PR commit packages the same executed file bytes; it was not separately run.

The old v0.34.16 CPU archive SHA256 is `9bbfff065299b3d6e863ecdeb0e54917788c1c0395cfa1d2b61bc40bf364932b`. Its daemon payload is `8ee5f661b2cab4808d5e859bcf60771335b4dbea549c26f3407e2328f8bf292a`. Source association074dac16 is the publisher's claim. Current retained artifact14183311941 and binary/source/config identities are in provenance.json.

Result artifact14198699992 ZIP SHA256 `f1907a56dd18ddeb7660b704f009cda123f177514f0aece0414db8de1d4caf12` was verified locally, including every ZIP member/extracted record. GitHub artifact expiry is 2026-11-23T05:14:46Z. This evidence tree retains the verified receipts beyond that retention window. Download the [test-only patch](wallet-transition-test-only.patch) and [evidence archive](wallet-transition-evidence.zip); the archive checksum is in [ARCHIVE-SHA256.txt](ARCHIVE-SHA256.txt).

`results/passing-native-result.json` is the actual sanitized result. `results/first-setup-failure.json` preserves first43807736044: the helper required20plusfee from one20coinbase, so neither consumer was reached. The only corrected fixture change is20→18 funding plus its explanatory comment; all transition assertions stayed unchanged.

The two forward consumers use isolated copies of the same healthy old chain/database. Assertions cover exact baseline descriptor/address/unspent/note state and selected spent-state non-resurrection, later receipt to old addresses, confirmed transparent/shielded sends with fees/change, relock/restart and unchanged old backup/database hashes. This adds a cross-package signer-wallet journey alongside existing historical-Bitcoin and same-build recovery coverage, without rerunning753/755/757.

## Reproduction

Actual executed CI entry point: `run-native.py` in the linked995f7dd7 run, following retained-binary and old dependency verification. The following is a reconstruction recipe for a compatible prepared source/build, not a separately executed command:

```sh
BTX_PREVIOUS_DAEMON=/absolute/path/to/verified/old/bin/btxd \
BTX_PREVIOUS_MODELNET=1 \
python3 test/functional/test_runner.py wallet_release_transition.py \
  --configfile=/absolute/path/to/current/build/test/config.ini -j1
```

Set the old ModelNet variable only when that build supports ModelNet; otherwise leave it unset. Use environment variables with the normal runner because custom CLI options would also reach its cache helper. The old executable must be verified and compatible with the shared framework/profile. There is no automatic binary download. Use disposable regtest data only.

Validation reused the53s native result without another run. Local preparation checks include exact byte hashes, AST parsing, two-file diff, whitespace/apply checks and one commit directly on the verified base. Full repository lint was not run; flake8 is unavailable locally.

Limits: no full-suite, Windows/macOS, crash/interrupted-write, downgrade, Qt, GPU/ModelNet-operation, live-wallet or independent old-build-reproducibility qualification. No product defect, schema migration, release guarantee or maintainer assignment is asserted. Credit JPP and Numair for the existing recovery work and coverage reused here.
