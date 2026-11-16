Bug: an existing unreadable or malformed governor permit can enable optional helper work.

- Use a governor-specific reader to refuse open/read/parse failures while retaining genuine absent-permit standalone behavior and existing upload limits. Both seed permission and automatic preservation use it.
- Windows: matched before/after consumer regressions (healthy control passes both; three defect cases fail before; all four pass after, 159 assertions). Corrected raw-file integrity and missing-parent recovery controls also pass (13 assertions).
- Linux: the same native two-helper workflow reproduces both unintended acquisitions before the fix; after it, malformed/EISDIR permits refuse acquisition, enabling recovers both original models, and a fresh model transfers with exact bytes. Both helpers stop and clean up.
- Evidence: [one entry point](https://github.com/sunnyriverr/btx/blob/e806396d8a98f3acc0723a7af4cdfe5ebd0849d2/contrib/devtools/windows-main-preflight/governor-repair/HANDOFF.md). Windows used the separate #746 fixture prerequisite on 1e2f8b5f; Linux exercised native POSIX transport. Windows daemon transport and the full Windows unit run are unqualified. Existing writer/fixture authorship remains in the base history.

Candidate: 8a3b19650886b59d398c3a853424dea26201acd6. The four source files match the qualified hashes; this clean commit packages that evidence rather than claiming a new whole-tree execution.
