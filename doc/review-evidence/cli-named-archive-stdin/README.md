# Wallet archive passphrases on stdin with named CLI arguments

**Fail before, pass after.** An identical native fixture on Ubuntu 22.04 ran the same three named-stdin backup cases and the named-stdin restore. The baseline returned RPC error -8 for all four. The candidate passed all four, and the new archives also restored successfully.

The fixture creates one encrypted, unfunded regtest wallet with an owned, labeled address. It verifies archive integrity, source relocking, restored encryption, and address ownership and label after unload and reload. Positional stdin, explicit named and mixed-prefix calls passed on both builds. A wrong archive passphrase and genuine duplicate arguments were rejected. The candidate also passed a round trip with equals signs in the archive passphrase and rejected supplying either passphrase twice.

[Executed fork CI run](https://github.com/sunnyriverr/btx/actions/runs/42970046296) · [Build and binary identities](provenance.json) · [Qualification verdict](qualification.json) · [Baseline observations](baseline/result.json) · [Candidate observations](candidate/result.json)

The named CI step runs build.py, which restores the verified checkpoint, enables the CLI target and builds the baseline. It then recompiles bitcoin-cli.cpp and relinks the candidate with the same libraries. The baseline CLI matched the stock binary by SHA-256. Both variants use the same retained daemon.

To replay the native fixture on Linux with either CLI and the matching daemon in a directory, use:

    python3 -u native_fixture.py --binaries /path/to/bin --expected-cli CLI_SHA256 --records ./records

Use the CLI SHA-256 from provenance.json. The fixture records the observed result for each case. The paired CI driver checks that each of the four affected cases fails on the baseline and passes on the candidate. Any passphrases in the fixture are synthetic.

The run covers an isolated Linux CLI and daemon with an unfunded encrypted wallet. A clean project build, other platforms, funded wallets and shielded recovery were outside this run.
