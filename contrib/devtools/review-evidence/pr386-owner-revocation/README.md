# PR386 concrete review followthrough

Test-only code `22c515741159c9051dc5b5d31b235d3a4bd61cba`, parent `b1be7920`, on #275's `fd3a905f`. Credit to [repch1c's concrete review](https://github.com/btxchain/btx/pull/386#issuecomment-6592257368) for the missing owner-revocation case and independent sensitivity observation. The product repair is unchanged.

- Added maintained owner-mandate-revocation case: initial freeze/revocation remains enforced; fresh unrelated direct-grant work survives repeat Tick and genuine Database close/reopen, then executes a harmless read.
- Added one existing-case assertion that candidate quarantine keeps an already-invalid active channel reported frozen.
- Two focused current cases pass once each; the identical final test source fails at the intended assertion when each relevant single-line protection is removed. No revised whole seven-case suite claim.
- [Actual execution/limits](execution/REPORT.md), [reviewer recipe](execution/REPRODUCE.md), [exact diff](execution/candidate.patch), [inputs/results](execution/execution-manifest.json), [internal artifact review](internal-review/FINAL-ARTIFACT-REVIEW.md).

Native macOS arm64 synchronous component, identified partial relink. The retained-workspace driver was executed; a separate clean-build recipe is provided but unexecuted. Source is maintained in the linked code commit/branch; the evidence directory is not a portable standalone build. Database reopen is not guard/Service restart, and no native sandbox worker, Linux/Windows, full-daemon or release qualification is claimed. Pilot empty-string accessor/output-directory failures are retained and distinguished from product failures. Other surviving mutation/source-rationale limits are documented rather than presented as tested.

Only selected text artifacts are public here: no binary, database, secret key or raw signed-record capture. Synthetic public captures remain local with hashes/counts in raw-record-catalog.json. Local user paths are normalized, with original/published hashes cataloged. SHA256SUMS describes this selected public directory, not the executor's broader local109-file package. Internal review did not independently run the test.
