# SwapNet reservation regression

Tested base: `8d6d8b1aabf371b12f2b1f5797b950fed7962d4e`.

The maker held 20,490 atoms after failed descriptor watch setup or a rejected
session insert. The initiator held 10,500 atoms after refund key setup failed.
Reopening SQLite preserved those holds without a session that could release them.
The fix commits the reservation, quote claim and initial session together.

macOS arm64, CPython 3.11.14, pytest 8.4.2 and cryptography 46.0.3. The existing
Pair fixture uses simulated chains and a real SQLite database. Watch and key
errors are injected, and a temporary SQLite trigger rejects the session insert.
Native daemon, wallet RPC and real-chain behavior were not tested.

From `contrib/swapnet`, with the listed dependencies installed:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m pytest -p no:cacheprovider -q tests
```

For the baseline, apply only the test-file portion of
[the patch](swapnet-reservation.patch) to the pinned base. For the candidate,
run the command on this branch. The baseline has three expected failures and
115 passes. The candidate has 118 passes, including retry, proposal replay and
restart with one funding operation per side in the fixture.

[Baseline](final-baseline.log) · [Candidate](final-candidate.log) ·
[Repch1c's original report](https://github.com/btxchain/btx/pull/630#issuecomment-6866329324).
