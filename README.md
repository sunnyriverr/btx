# Modelnet subscription mandate save failure and restart

The acceptance question is whether the real file-backed helper leaves a refused reservation out of its budget, preserves an existing saved reservation, then accepts and persists the same event exactly once on retry. Compare #542 at 08d1ba80 with the same tree plus #543 at 7fa42393. Both target release base dac9aee5. GitHub showed no comments, reviews, or overlapping live helper result on either PR at the start. The author exercised a helper store reset in #542 and a direct store save fault in #543.

The harness uses an isolated macOS arm64 helper with a disposable Unix socket and data directory. It blocks only the sibling temporary state path with a directory, compares the old state bytes, checks the RPC budget and activity, removes the blocker, and replays the same reservation before and after a full process restart. A fresh event after restart checks that the budget can still advance. [Harness](run.py) · [Source verification](github-source.json)

## Result

The same harness failed its rollback assertion with #542 alone and passed with #542 plus #543. Each variant ran once on macOS arm64 with AppleClang 17 and static OpenSSL 3.6.3. The helper target was built with Modelnet enabled, wallet and Metal disabled, and no wallet or peers attached.

| Check | #542 alone | #542 plus #543 |
| --- | --- | --- |
| Before the fault | 20 principal, 2 fee, one reservation | Same |
| Save blocked | RPC rejected and saved bytes stayed intact. Live budget incorrectly became 70 principal, 7 fee and two reservations. | RPC rejected and saved bytes, live budget and existing reservation stayed intact. |
| Retry after removing the blocker | Both reservations became durable. | The refused event was admitted once, giving 70 principal, 7 fee and two reservations. |
| Replay after a clean process restart | Totals and reservation IDs were stable. | Same. A fresh event advanced the totals to 80 principal, 8 fee and three reservations. |

The checks also covered outstanding exposure and concurrent reservations, an already-saved event replay while writes were blocked, and zero automatic spending. The baseline demonstrates premature in-memory accounting after rejection. Both variants recovered after writes resumed in this sequence. Scope is the helper's local RPC and one forced temporary-file failure. Host files and running services were isolated. The disposable RAM volume was detached after both helpers exited.

[Baseline result](before-result.json) | [Combined result](after-result.json) | [Source hashes](source.json) | [Harness](run.py)

The harness takes a variant label, an absolute path to the corresponding btx-modeld binary, a disposable scratch directory and an existing evidence directory. Exit 42 means the rejected reservation remained in memory after the forced write failure. Exit 0 means rollback passed.
