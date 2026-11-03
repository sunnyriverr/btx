# Qualification registry recovery

Product code `9f6f3e13e65073e4704f0ea08831e9ed7bdc4105`, based on current `btx-035/swarm` at `cbf65894`. The initial Windows failure was [reported by repch1c in #356 item14](https://github.com/btxchain/btx/issues/356#issuecomment-6592708241). Further source review found a cross-platform recovery defect: a valid outer registry containing an invalid row reports quarantine without moving the file, while bad field getters can throw past recovery.

The two-file product branch closes input before rename, uses one checked quarantine path outside a narrow parsing/getter exception boundary, and adds native Boost test bodies. Accepted schema/value rules, ordinary persistence and issuer admission semantics remain unchanged. A first failed load stays unhealthy; a new empty instance knows none of the old challenges.

- [Execution report and limits](execution/REPORT.md), [exact two-file patch](execution/patch.diff)
- [Staged baseline](execution/baseline-run.json), [added getter baseline](execution/baseline-fields-run.json), [five-case candidate](execution/candidate-run.json)
- [Explicit aggregate result check](execution/candidate-result-validation.json), [recipe](execution/REPRODUCE.md), [internal audit](internal-review/FINAL-REVIEW.md)

Native Mac component evidence: full qualification TU and exact maintained Boost bodies with disposable-directory-only fixture adaptation and pinned reused libraries. Preliminary four-case baseline is two pass/two intended fail; the added final-harness getter case also fails. All five candidate cases pass, including real CPU toy work, issued/redeemed persistence, exact corrupt-byte preservation, real directory-collision failure, and fresh-instance unknown/unredeemable old challenges. This was not a clean five-case baseline run.

The local observation wrapper's shell0 means builds/invocations completed, not that cases passed. Read all_passed and individual statuses, or use the documented separately executed result assertion. Native test_btx integration has not run here. The selected historical recipe depends on the retained workspace's source/header projection and identified libraries; this evidence directory is not a portable clean-build package. For ordinary review use the actual product branch and its maintained compute_profile_tests; the clean native integration route is documented but unexecuted. The full4047-file local catalog/header projection remains local and is hash-identified separately.

Windows-after/MSVC sharing, full test_btx, actual daemon restart, full clean build, GPU/mining/device admission and other-platform qualification remain unverified. Closing the input addresses the reported sharing mechanism by source reasoning, not a native Windows result. New registry instance reopening is not a node-process restart. No wallet, live node, GPU, VM or financial operation ran.

Only selected source/text artifacts are public: no library/binary, private key, user registry, or wallet data. Paths are normalized with original/published hashes. Public SHA256SUMS describes this selection, not the broader localcatalog. Internal review is source/artifact audit, not another native execution.
