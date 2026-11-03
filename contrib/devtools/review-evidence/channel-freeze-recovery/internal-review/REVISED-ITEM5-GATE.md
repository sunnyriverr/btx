# Revised item 5 implementation gate — APPROVED

BTX test 1 independent reviewer `/root/channel_recovery_review`, exact fd3a baseline. This supersedes the conditional conservative-policy gate in CODE-BASELINE-GATE.md. No reviewer runtime/build/VM/product/shared/public writes. Model inherited/unverified.

Approve local implementation and one candidate run with the SAME final harness. No additional matrix requested. Final source/artifact/results review remains outstanding.

The coordinator selected the behavior-preserving scope. Only lifecycle.cpp changes; Broker stays unchanged. The renewed signed-lease case is a passing compatibility and fresh-incident rearm control in both variants, not a third established defect. The two baseline failures remain actual unrelated permit SEC_PERMIT_REPLAY after repeated Tick/Database reopen and valid successor destruction. Four safety/compatibility groups pass.

Every Tick recomputes active Eligible independently of its durable channel-frozen-active/<name> acknowledgment. Current owner validity is checked independently. A matching acknowledgment suppresses side effects only for the currently failing same active binding; it does not confer admission. Current-owner observed eligibility clears acknowledgment, so a later same-ID failure is a fresh incident. Qualified previous recovery is attempted before dedup on every failing Tick. Activate and rollback clear the marker inside their existing transition transactions. Freeze acknowledgment commits with frozen state/global prepared-permit revocation/event. No schema, header, ABI, OS API or conditional platform change; namespace is injective and unused elsewhere, and none sentinel cannot equal a digest.

New owner/mandate failure during a canary is not skipped: owner_current=false enters the transition and clears candidate. Already frozen/empty/same binding need not repeat destructive side effects for continued invalid authority; direct Stage/Activate authority gates remain. A new Follow sets awaiting and therefore does not hit that frozen-state early return. Recovery candidate ineligibility freezes if active remains invalid. Ordinary-canary first incidents, fresh successor failure and rollback retain existing failure handling. Existing missing MeshRequireLive in rollback is out of scope.

Existing Broker re-admission keeps expired/revoked capsules unusable; transiently eligible old active during a signed successor canary retains baseline authority. The permanent quarantine/Broker fence was rejected as an unsupported compatibility policy change, and the earlier contract recommendation to require it is superseded.

The same fixture builds actual initial lifecycle state via synthetic signed observations and observes actual descriptor-scoped reads after permit repeat/reopen and successor activation. Synthetic signed canary receipts are not native execution. JSONL capture affects artifact output only; prior SEC_TEXT getters, collision correction and aggregate canonical-array output-limit pilots remain fixture history, not product findings. A Database reopen is not a guard restart. Reused dependency source closure was independently verified earlier (239 repository rows, 8 generated/config files, 14 objects/archives, zero mismatches); exact final receipts must continue to say partial relink/reused objects, not clean build.

Reviewed identities (SHA256):
- proposed.patch: `96fe88dfd0425b6ccab7a657822fb4846266b63923ef64afbda4e0f9ae20ec2d`
- harness.cpp: `86e85ff04e8933103b80f25d54f217935192099da43d27c028920777d26d96e2`
- results/baseline.json: `ce2a0eabad92a56f957c87d16e188eb38ea6e252f5f9dd5d1bab6e3df2d1bb85`
- baseline-build-run.json: `6ff42a0149176208900bd4adbfae077e6284b45ab78f4d8f9f1ccd2b94fb3a65`
- source-closure.json: `67eae338104c2aad407108fa6db10bdd1a9f505974c9a7291822c90e8b98359c`

Signed-record capture: 3996940 bytes / 421 canonical JSONL records. Final baseline: 4 PASS / 2 intended FAIL, return code 1; Mac arm64 main-thread component only. No Service/native worker/default-stack/VM/full-node/other-platform qualification.
