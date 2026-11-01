# Supervisor cancellation candidate

Bug: a supervisor helper RPC can delay node shutdown; this branch contains the exact previously tested corrected candidate, including the Windows send-error API correction.

- Base: `70e35da0e43cdf0fc099076786b3441e5db1d1a9`. Three product files; no other production change. Code commit is separate from evidence.
- macOS: four shutdown fault cases fail before; all six cases pass after. Ordinary 123-second calls and ownership of external helpers remain intact; disposable strict-Metal node restart/progress verified in the earlier run.
- Linux: same final native Alpine/aarch64/musl component harness has four fault failures before and all six cases pass after. Both versions preserve long calls, application refusal and external-helper reuse. This uses the complete supervisor translation unit and extracted transport bodies with explicit support adapters, not a full helper/node build.
- No native Windows run, real send-buffer-saturation oracle, glibc/full build, full suite, mainnet or release qualification. The Mac Windows-error tests inject API semantics; they are not Windows execution.

## Reproduce and inspect

From `linux/source`, run `sh build.sh` then `python3 regression.py` on a disposable Linux host with GCC/C++20 and Python3. Expect baseline fault failures as documented; the script uses local sockets and synthetic children. Read `linux/LIMITS.txt` and `linux/REPORT.md` first. Runtime is approximately three minutes. No command was rerun to prepare this branch.

`mac/` preserves the published corrected report and unchanged runtime/contract harnesses. Those scripts need the recorded matching baseline/candidate binaries and synthetic blocks; this branch does not claim a turnkey full Mac build. Reports retain historical completion/private wording; the current branch README supersedes delivery status only.

The product patch is applied in the first commit, not merely attached here. `provenance.json` records exact file and patch identities. `linux/combined-cancellation.patch` is the same patch for reference: do not reapply it to this branch.

## Credit and provenance

Candidate implementation/testing: Sunny River, with AI assistance. Existing source authorship and copyright are unchanged. JPP supplied review/handoff guidance and authored existing helper lifecycle work; his original commits remain in the base history. His earlier ACK of #354 is not an ACK of this separate cancellation candidate. No additional co-authorship or independent verification is implied.

Original scoped report: https://github.com/btxchain/btx/pull/354#issuecomment-6553542268
