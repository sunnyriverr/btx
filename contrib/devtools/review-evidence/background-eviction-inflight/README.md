# PR370: in-flight root exception review

Test-only follow-up `5deb327871efbca832e1a4e420f76dad74ff6b41` to product/test commit `b37742560c62ecffce5ea29ca233c23036c9bbd2`. Product code is
unchanged. Extends the existing evicted-to-root test, following repch1c's review;
Jpp-matata's snapshot fixture and prerequisite credit remain intact.
AI-assisted work by Sunny River.

A real height40 request is in flight when evicted height16 becomes the next
background root. Same final test: pass3/3, all40 locally verified, snapshot
validated and source connected. Remove only `&& !background_root` from the
in-flight early return: fail3/3 at the missing root16 GETDATA assertion.
Four adjacent controls pass once. Test source/binary identities are in summary.
Two fixture pilots were corrected and are disclosed in pilot-note.txt; they are
excluded from final counts. No product patch was needed.

Mac/M4 Release focused CMake-library link, main+peerman+lifecycle test objects;
mock replay and null transport. No new full-suite, GPU, Linux/Windows, mainnet,
restart or default-policy qualification. Prior native1024 result is unchanged.

## Reproduce on the code branch

Build test_btx using the repository's normal macOS instructions, then run
`peerman_tests/snapshot_evicted_body_becomes_background_root` in a fresh process
three times. For the negative control, change only
`!mapBlocksInFlight.empty() && !tip_chain_needed && !background_root` to
`!mapBlocksInFlight.empty() && !tip_chain_needed` in src/net_processing.cpp,
rebuild the node library/relink test_btx, and repeat the identical test. Expect
exit201 at the root16 assertion, not an unrelated timeout. Restore product code.
The recorded focused link inputs are included; that is not a full-test_btx claim.

## Scope agreed for the fold

Hash-wide tombstones can suppress a different netgroup with capacity available.
Changing that requires requester-room controls and is not this follow-up.
Farther arrivals can still evict retained bodies; the native1024 case fits one
download window and does not qualify mainnet ranges spanning tens of thousands
of blocks. Keep those limits in #340. Keep #370 open until adoption is verified.
