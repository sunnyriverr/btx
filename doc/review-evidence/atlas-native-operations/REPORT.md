# PASS — requested native Mac operation-dialog checks on afd65919

Exact Atlas target: afd6591970e7f8d65871412b9d7cf03b48f30b97. Native macOS26.5.1 arm64, unchanged retained app SHA2562b3973619f7ee07e17fc2b8b9f938720dffe35c1bf4ebb18f92a592b06a1af6e. Answers Numair’s PR273item3 request6602199759. Fresh preflight confirmed the head unchanged and no new matching public completion. Prior294/290/295 component evidence was reused as context, not rerun or relabelled as native evidence.

## Observed results

Through Tools → RPC console → exact method → Open command → Prepare for native review, each of exportwalletbundle, dumpmasterprivkey and z_exportviewingkey with [] parameters displayed KEY_EXPORT_DENIED and the exclusion message. These are transcribed native accessibility observations retained in progress.json; no screenshots of these three denials are claimed. Node RPC logging recorded zero calls to all three methods.

Through the same supported UI, walletprocesspsbt was prepared with a synthetic unsigned PSBT (nonexistent input, deterministic public witness output1000atoms), sign=true, bip32derivs=true. The normal ALL and requested NONE|ANYONECANPAY native dialogs displayed the same complete transaction skeleton and matching PSBT SHA2565a6b33ffda03c69567e2e9f9d467e906af99af632af60846602d435fbccbef50. Both replaced raw PSBT text with a placeholder in the displayed parameter list.

The user-supplied ALL screenshot shows Sighash: ALL with no signature-reuse warning. The user-supplied non-default screenshot shows Sighash: NONE|ANYONECANPAY and the explicit warning that the signature can be reused in a different transaction. The full visible dialogs were read from those images, not inferred from source. User cancellation returned both cases to CANCELLED in Atlas; the ALL screenshot and later native AX observations confirm those states. A previously uncaptured non-default observation was also cancelled; it was repeated only because the warning content had not been established.

The allowed signing-preparation route reaching a real native dialog is the relevant control against blanket refusal. The ALL/non-default comparison distinguishes specific warning behaviour. No real wallet or keys were needed. This is acceptance of the integrated requested behaviour, not a new product repair or before/after campaign.

## Fixture and unsuccessful setup/pilot

The retained older node binary03a3fb602e0a0dea77583f774ecf516f5875137829c2a9f6c03637f925300fc6 supplied local regtest RPC infrastructure only; it does not qualify the current node. Wallet support was enabled so its help inventory advertised the methods, but no wallets were created or loaded. No peers/listening/modelnet. Rejected initial OP_RETURN fixture output was corrected to a normal public witness address; this was unsupported fixture input, not a product defect.

Native file-picker automation repeatedly reset the GoTo sheet. A private mode0600 visible cookie copy and user assistance completed the normal connection. LIVE LOCAL was verified via native AX. No replacement dialog or host-state injection used.

One initial signing-review pilot passed its confirmation before it was captured. The acknowledgement cause is not established. It reached walletprocesspsbt and the empty node returned RPC_-18 (no wallet). This was not cancellation evidence and is not presented as such. Final log has exactly one walletprocesspsbt call, from that pilot; later cancellation attempts added decodepsbt calls but no additional walletprocesspsbt invocation. There were no wallets/keys/funds/signatures. The tool timed out while the real macOS modal was open; user-provided screenshots and manual cancellations supply that part of the native evidence. This assistance is disclosed, not independent reviewer execution.

## Scope and evidence

summary.json records exact identities, results, counts and evidence hashes. fixture.json contains public synthetic unsigned test data. user-evidence.json hashes the three full original screenshots retained under user-evidence/. They include background chat and remain private; do not upload originals without reviewing that surrounding material. node-sanitized.log retains RPC method evidence. cleanup.json verifies exit/removal. The native-control excerpts are manual transcriptions from tool output; no continuous UI recording is claimed.

Not covered: separate recursive/nested-secret redaction, named/wrapped parameter forms, HTLC/timelock warning variants, actual signing/payment/broadcast, Windows/Linux/full suite or release qualification. The PSBT placeholder observation is not a general secret-redaction qualification.

## Closeout and next action

Quit the exact owned app using its native menu; stopped owned node by RPC and verified both exited. Verified listwallets remained empty before shutdown. Removed owned scratch and both temporary cookie copies, including the one in Documents. No production/PQWallet/shared source changes; app/source/build retained unchanged. Publication authorized after testing and final review.

Final internal claims review passed: review/REVIEW.md. The reviewer inspected all three original user screenshots, checked metadata/hashes and scoped claims, but did not independently execute the native test. This public package includes transcriptions and hashes, not the full screenshots with background conversation. No image manipulation or fabricated screenshot is supplied. AI-assisted execution and internal review.

Exact Atlas build/source provenance is already public in the prior sole-link evidence package, linked from README.md. This result is a separate requested native operation-dialog check; it does not repeat that test.


Lesson: macOS native modal observation needs a plan for the control-tool timeout. Ask for an exact screenshot/content observation before cancellation, rather than treating a terse cancellation acknowledgement as proof of warning text. Keep uncaptured pilots separate from measured results.
