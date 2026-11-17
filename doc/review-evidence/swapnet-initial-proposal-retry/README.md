# Saved initial proposal retry — Mac evidence

**Stock fails both missing-first-send recovery cases; the candidate passes30/30 cases, zero skips.**

Code: [2cb8bd213e0ffd7ef1215e1b614c6ac5852a3075](https://github.com/sunnyriverr/btx/commit/2cb8bd213e0ffd7ef1215e1b614c6ac5852a3075), one commit on release-0.34.17 `bd847e2b986722c1723b4cd60988d4f4908452d4`. Only Coordinator, Journal and the maintained regression change. Reuses the original SwapNet Application/SQLite wire fixtures; credit to their existing authors, including Numair and repch1c.

## Problem and correction

A SQLite outbox INSERT failure after the intent/reservation saves leaves `proposed` durable but no proposal to send. On stock, healthy same-accept and clean Application reopen/resume return the saved session without delivering it. The reservation remains held until normal cancellation/expiry. This is an unfunded liveness failure; no theft or lost principal was demonstrated.

The correction explicitly retries only the saved original initiator proposal. Keys, secret, nonce, reservation, fee caps and absolute deadlines stay frozen; saved held authority is rechecked. Already queued/acknowledged/not-due packets are not recreated. Conflicting stored routing/payload and restored or financially progressed missing-send states refuse recovery. No background resend, schema, funding or refund change.

## Executed results

Mac ARM64/Python3.12.14, production Application/Coordinator/Journal/SQLite, injected SQLite trigger abort. Same final harness SHA256 `e76abc5870223306f531870f8c771f713c3f9270528d584f15e2a2cb69e42201` before and after.

| Run | Result |
| --- | --- |
| Final stock, missing-send accept/resume selected | 2 intended assertion failures;28 deselected |
| Final candidate, entire maintained regression |30 passed/0skipped,2.39s |
| Review correction control on first candidate | stored-recipient conflict failed; payload/envelope conflicts passed |

Successful recovery delivers the original intent and settles once per leg. Controls preserve frozen reservation/key/secret/budget identity, repeated write/sign refusal and healthy retry, existing packet deduplication beyond the delivery page, revoked/expired mandates, owner permissions, original deadline/clock checks, lost reply after enqueue, safe restored/prepared refusal and cancellation release exactly once.

Logs and loaded module hashes: [baseline](baseline.log), [candidate](candidate.log), [qualification](qualification.json), [final review](FINAL-REVIEW.md). The review-discovered routing gap was corrected before publication; [first-candidate control](conflict-before.log). Older28case evidence is superseded and retained locally, not added to final coverage counts.

The actual local launcher was `python3.12 -B run_repair.py baseline -k missing_proposal_retry_and_reopen` then `python3.12 -B run_repair.py candidate`, with frozen flat baseline/candidate package trees. [run_repair.py](run_repair.py) records that execution context; local paths are redacted. It is not a turnkey full-repository runner.

## Maintained-test reproduction recipe

This portable recipe was reconstructed from the executed harness; it was not rerun merely for packaging. Use a separate checkout of `bd847e2b986722c1723b4cd60988d4f4908452d4` and a supported Python3.12 environment with the package test dependencies. Copy `contrib/swapnet/tests/test_initial_proposal_retry.py` from the code commit into the base checkout; from `contrib/swapnet`, run `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3.12 -m pytest tests/test_initial_proposal_retry.py -k missing_proposal_retry_and_reopen -q -p no:cacheprovider` (expected2missing-outbox failures). Apply the code commit and run the whole test file (expected30pass). Existing requirements-tested-dev.txt describes dependency pins.

## Limits

Chains, identities/financial signers and transport are deterministic fixture simulations. Restart means clean Application/SQLite/vault reconstruction in one Python process, not native btxd restart, abrupt-kill durability or a native funded swap. No Linux/Windows, native PQ, embedded-worker, full-suite or release qualification. The #814 product patch applies cleanly; combined runtime was not tested. Prior original-refund evidence is reused; refund execution was not repeated for this unfunded proposal boundary.

Public copies redact local home/workspace paths. Source/test SHA256 values remain exact; MANIFEST.json hashes the published sanitized evidence bytes. No wallet/chain databases, keys, credentials or storage-cleanup archives are published.
