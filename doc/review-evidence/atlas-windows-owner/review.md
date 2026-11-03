# Atlas elevated owner acceptance review

## Pre-execution review

**PASS for the bounded source-reviewed experiment.** No runtime result is claimed here. Reviewer read the current fixture/workflow and the current Atlas check supplied in task context. No tests, builds, downloads, network requests, source changes or publication were performed by this reviewer.

The fork workflow targets only codex/ci-atlas-owner, uses standard windows-2025 with read-only repository permission and an eight-minute timeout, and fetches exact source commits. No external action, package installation, artifact/cache upload or scheduler is present. Actual runner token privileges, native shell availability and ownership-setting support remain execution gates.

The fixture requires an already elevated administrator token. It creates one GUID-named directory under RUNNER_TEMP, restricts its inherited access, and copies the system notepad binary into that directory without modifying the installed source. It explicitly establishes and verifies the current identity as normal owner. The test's ownership changes target only that copy; no workstation, wallet, repository or installed binary permissions are changed.

The owner transition verifies the resulting SID is S-1-5-32-545. ACEs and content hashes must be unchanged across the transition, and the initial ACL excludes the broad-group SIDs under test. For both native Windows PowerShell and PowerShell7, the adopted checker must pass the normal and restored controls; the older checker accepts the broad-owner fixture, while the adopted checker must reject it with the exact owner diagnostic. An explicit broad-write diagnostic fails the case, guarding against taking the wrong refusal route.

Each checker invocation captures exit status and compares pre/post SDDL and file hash, so its read-only property is measured. The source scripts are extracted as original Git bytes with commit/hash records, rather than adapted for the fixture. The host records actual shell versions; source review does not prove them in advance.

Restoration must recover the complete initial descriptor and content hash before the final controls. Finally performs another owner restoration and deletes only the owned temporary fixture. A nonzero cleanup restoration status or surviving fixture prevents final success. Unexpected failures propagate through the fixture script and job; the always-log step does not turn a failed test step green.

## Claims boundary

A successful job would qualify this elevated, owner-only ACL case on the recorded Windows runner and shells. It would not qualify every localized code page, installer behavior, a complete Atlas desktop session, production filesystem policy or release readiness. Failure to obtain the existing token/fixture conditions is setup or NOT_RUN, not a product failure. Preserve raw logs, observed owner/ACE/hash state, script identities and cleanup outcome before asserting acceptance.

Reviewed fingerprints:

- check_owner.ps1: 57817f5dcaa1a24318f8190cbd30ca64389581095d0affd2a59145c6d8f23fcc
- owner-check.yml: ee0eba6d23655ac10718577b4913004c33a06688e6ad852b5aecb6f8b788d840


## Final native artifact review

**PASS.** Run41651982533 completed successfully on its first attempt at workflow commit e0a7320ea0592e759533c65dad72fb60b70cb7ef. Every job step succeeded. Raw setup identifies Microsoft Windows Server2025, image windows-2025-vs2026 version20261030.294.1, build26100. Shells were Windows PowerShell5.1.26100.33648 and PowerShell7.6.9. The recorded existing administrator token check is true; ownership-setting operations succeeded without an elevation or new-access step.

All eight cases match their expected exit codes: normal-current0 in each shell; Users-owner baseline0 and current1 in each shell; restored-current0 in each shell. Both current refusals include the exact owner: BUILTIN\Users (S-1-5-32-545) diagnostic and no write-grant diagnostic. The older check accepts that same ownership condition. This demonstrates the adopted owner check, rather than an unrelated broad permission refusal.

Independent artifact checks compared every before/after snapshot, not just aggregate booleans. Each checker invocation preserves its full SDDL and content hash. All four Users-owner cases record ownerSID545 with the same DACL entries and binary hash as the normal fixture. Both restored cases equal the complete initial snapshot. Final cleanup reports successful owner restoration (exit0) and fixture removal. These are observed job records, not another filesystem inspection or independent runtime.

Both extracted checker SHA256 values independently match their exact Git blobs at acbf7efb and afd65919. The raw logs.zip digest independently matches summary.json. Independently stripping timestamp prefixes from the raw Record results step and parsing its result.json reproduces decoded/result.json exactly. No additional test, network request or publication was performed by this reviewer.

The qualified scope is the elevated owner-only case on a disposable copied executable under the recorded WindowsServer/PowerShell environments. It does not qualify Windows11 desktop/installer behavior, every localized code page or ACL policy, a complete Atlas application flow, production wallet/filesystem policy, or release readiness. The result supports a concise existing-thread acceptance handoff; no further repeat of this campaign is justified by the evidence alone.
