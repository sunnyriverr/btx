# Negotiation response recovery

**Mac before/after: four intended interruption failures before; all16 maintained recovery cases pass with the repair. Nine selected existing commit/safety controls also pass. Zero skips.**

Code: [e21cbab4](https://github.com/sunnyriverr/btx/commit/e21cbab422fc197ba7b2ce04ce3d5db9f3d05aa2), parent `ef854454075845b1cba3c1352884ac78af770dc0` on release-0.34.17. This includes Numair's adopted749/750/751 and later refund-fixture timing correction. Earlier0afc qualification was not substituted for these current-base runs. All30 baseline package blobs match GitHub; the nine-control test file also matches current upstream.

## Problem and fix

After saving an offered or committed session, a process can stop before queuing its agreement/commit response. An inbox admission then masks the unfinished handler on replay. The initiator can fund once while the responder stays offered; the original refund protects that stall.

Apply existing bounded completion tracking to proposal, agreement and commit. Mark completion after normal handling and before ACK; an ACK failure retains completion. Existing saved-response handlers preserve terms, financial signatures, keys, reservation and budget. There is no new signing authority, funding path, deadline extension, schema migration or network retry framework. A normal proposal decline also counts as completed handling.

## Tests actually executed

macOS ARM64, Python3.12.14, actual Application/SQLite and deliberate child exit73/reopening. The same maintained test bytes were loaded against isolated before/after source directories:

| Invocation | Result |
| --- | --- |
| baseline, new regression, `-k interrupted_negotiation` | 4 intended failures,12 deselected,0.79s |
| candidate, full new regression | 16 passes,zero skips,2.65s |
| candidate, existing commit controls selected below | 9 passes,11 deselected,zero skips,0.96s |

The cuts are after saved offered/committed state before outgoing response, and after handler/durable response before completion receipt. The second cut proves completion bookkeeping; it is not another baseline one-sided-funding reproduction. Controls cover failed response/receipt INSERT, saved-payload retry, no new financial signature/keys/secret/reservation, completed duplicates, ACK failure and reopen, legacy admission, durable decline, exact once-per-leg settlement, original early/mature refund and consumed-budget accounting, invalid/expired packets. Existing controls cover four commit interruption cuts, four legacy authority/terminal refusals and receipt capacity/expiry/cascade.

[Manifest](manifest.json), [baseline](baseline.log), [candidate](candidate.log), [existing controls](commit-controls.log), their execution receipts, and [patch](candidate.patch) are retained here. Paths in public logs/receipts are normalized; source/test hashes are hashes of original loaded bytes. Individual records—not merely a passing process exit—establish the case counts.

## Reconstruction recipe

This is a portable reconstruction using the maintained test; the local execution used the isolated loader recorded in the receipts. Install the repository's tested Python requirements. Create two clean worktrees at `ef854454` and `e21cbab422fc197ba7b2ce04ce3d5db9f3d05aa2`. Copy only `contrib/swapnet/tests/test_negotiation_response_recovery.py` from the candidate into the baseline worktree. In each worktree's `contrib/swapnet` directory:

```sh
# baseline: expect four failures at missing response/completion, not setup
python3 -m pytest tests/test_negotiation_response_recovery.py -q -k interrupted_negotiation
# candidate: expect16 passes on Mac/Linux with fork
python3 -m pytest tests/test_negotiation_response_recovery.py -q
# candidate existing controls: expect9passes
python3 -m pytest tests/test_inbox_commit_recovery.py -q -k 'commit_replay_after_actual_exit or pending_legacy_commit_preserves_refusals or receipts_share_capacity_and_expiry'
```

No chain, wallet or production files are required. Upstream pyproject testpaths discovers the maintained new test normally. Fork-only cases explicitly skip on Windows; no Windows execution is claimed.

## Limits and credit

Chains, financial signing and transport are simulated. Not native funded BTX/Bitcoin/Ethereum, btxd/embedded integration, Linux/Windows execution, full-suite or release qualification. Replaying after response-save/pre-receipt may create another transport envelope with the same saved financial payload; no claim of one envelope. Legacy completed agreement without receipt can still hit existing terminal SESSION_BINDING refusal; that is not weakened. A peer remaining absent can still require the original refund.

Reuses Numair/repch1c's existing Application/execution fixtures and builds on adopted814/816. This focused repair adds only the remaining negotiation-response completion boundary.
