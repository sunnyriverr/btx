# Operator recovery guide — local documentation review

## Result and scope

One100line/656word section drafted for doc/managing-wallets.md, after the browser bundle section and before native backup bundles. It explains the missing-history route qualified by #753 without presenting the unpatched release as working. It is a local one-file documentation proposal, not an edit to the published PR or its three tested code/test files. No new native tests, CLI/RPC calls, wallet operations, build or post.

Current review target: release-0.34.17/1e2f8b5f, plus the already published #753 correction for the deferred encrypted restore prerequisite. At the source check #753 remains open at ea76a312, without reviews/comments; release1e2/main074 unchanged. Do not infer adoption from this draft.

## Evidence mapping

| Guidance | Source or existing execution supporting it |
| --- | --- |
| Successful import differs from complete scan; rescan=false does not suppress all shielded scanning | ImportBtxWalletBundleIntoWallet's post-install MaybeRehydrateSpendingKeys; #753 fixture incomplete-state assertions |
| Failed restore can leave a destination; its presence is not seed-installation proof | restorewalletbundle creates before import/history preflight; its catch relocks and does not remove the destination. New guide explicitly excludes a failed destination from the later same-database route |
| Existing-wallet authority must not be overwritten | HasShieldedKeyMaterial guard and unchanged maintained wallet_importbundle_shielded.py, PASS47s in43770868266 |
| Locked backup preserves the encrypted restored database; do not use a plaintext export as its substitute | backupwallet RPC implementation, fixture walletlock/backupwallet/copy digest checks; managing-wallets credential sections and encrypted-backup guide |
| Root-endpoint unload and startup false | rpc/wallet.cpp unloadwallet help/handler; rpc/client.cpp Boolean argument conversion; exact fixture unloadwallet(name,False) |
| Full-history same-network continuation under a fresh name | Native corrected fixture restores same backup on peerA, not the seed bundle; original/control wallets unloaded. Guide narrows to same corrected build rather than promising cross-version support |
| Passphrase prompt syntax | bitcoin-cli.cpp stdinwalletpassphrase allowlist/read/insertion; rpc/client.cpp numeric timeout conversion. The flag supports walletpassphrase, not restorewalletbundle; the draft does not invent a fresh-restore invocation using it |
| Full rescan from0, no stop_height; missing-history and aborts are failures | transactions.cpp RescanWallet history preflight, partial/stop restrictions and scan-status handling; fixture explicit missing-history rejection and later full rescan |
| Integrity flags after unlock plus known receipt checks | backup.cpp integrity report fields/conditions; fixture exact note/balance/integrity checks. Local flags are not a promise of arbitrary address-gap coverage |
| Runtime claim boundaries | #753 qualifier: Ubuntu24.04 CPU regtest, two selected tests, actual pruning/restart/recovery/confirmed use. CLI spellings were source-checked, not run; timeout600 is illustrative versus fixture999000 |

The draft links existing credential/address-discovery guidance instead of repeating the full archive procedure. It does not prescribe deleting a failed wallet, overwriting its seed, moving user coins, editing shielded state, or treating pruning-off as restoration of historical blocks.

## Review and static checks

INDEPENDENT-REVIEW.md is a bounded internal source review, not platform replication. No blocking inaccuracy found. Its wording suggestion distinguishing tested JSON-RPC from unexecuted CLI examples was incorporated. Owner review also split source unload and full-history unlock from preceding operations so restore/backup success is checked before continuing.

The patch was dry-run checked against a separate exact upstream preimage; proposed file reduces to that preimage after removing exactly the inserted section. Whitespace, Markdown fences and links/anchors checked locally. The first exploratory git apply check was pointed at the already modified candidate and failed; it was not a source/product failure or native test. Correct isolated preimage check passes. See static-checks.json for final hashes. Published fix/regression source bytes remain unchanged.

## Next action and boundaries

Keep this proposal local. It can become a documentation companion to #753 after the maintainer's review/adoption target and publication authority are settled. No standalone PR or extra comment merely for activity, and no new native run just to validate these source-checked explanatory examples. Recheck the source/build prerequisite before any publication; remove or revise the transient adoption wording only when supported by actual incorporation evidence.
