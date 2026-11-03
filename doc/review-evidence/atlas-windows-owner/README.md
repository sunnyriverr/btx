# Atlas elevated Windows owner acceptance

Scoped PASS on afd6591970e7f8d65871412b9d7cf03b48f30b97. Completes Numair's owner=Users request on PR273 (comment6602199759), left unrun in repchic's complementary nativeWindows results (comment6603952009).

Run: https://github.com/sunnyriverr/btx/actions/runs/41651982533 (attempt1).
Exact fork workflow/harness commit:e0a7320ea0592e759533c65dad72fb60b70cb7ef.

## Observed results

WindowsServer2025 build26100, existing elevated administrator token. PowerShell5.1.26100.33648 and7.6.9. The harness creates a GUID temporary directory and copies system notepad.exe into it; only this owned copy has its owner changed. The DACL grants only fixture creator, SYSTEM and Administrators. Installed binaries, workstation settings and production wallets are not changed.

Eight invocations total:
- Adopted check with known normal owner: exit0 in both shells.
- Same file with actual owner SID S-1-5-32-545 (BUILTIN Users): older acbf7efb check exits0; adopted afd65919 exits1 with the exact owner diagnostic, in both shells.
- Original ownership restored: adopted check exits0 in both shells.

Owner change preserves access rules/content. Every checker call preserves its before/after SDDL and content hash. No broad-group ACE or explicit write-grant diagnostic explains the refusal. The fixture is restored to its initial complete SDDL/hash, then removed; final cleanup restoration exits0. Pinned checker scripts are extracted as exact Git bytes; hashes in summary/result match the two source commits. Baseline normal/restored rows were not separately run.

## Evidence and entry point

summary.json is the compact result; result.json contains all before/after observations and source identities. actions-log.txt preserves the original downloaded job transcript. Individual logs are derived by removing Actions timestamp prefixes; review.md records source and final artifact review. The original raw ZIP is retained locally and its hash is in summary.json. Execution and internal review used Codex; review is not another independent execution.

The supplied harness/workflow are the committed source used for the job; Git checkout may normalize harness newlines on Windows. The checker scripts themselves are extracted through git show and written as original bytes. No new product source or test execution accompanies this package.

To use the recorded entry point in an already elevated disposable nativeWindows environment with Git, Python3, WindowsPowerShell andPowerShell7 present, the repository must contain both pinned Atlas commits:

```powershell
./check_owner.ps1 -Repo C:\btx -Out C:\checks\owner-new
```

The output directory must be new and its parent exist. RUNNER_TEMP must point to the owned temporary area. This case refuses a missing existing administrator token; it does not elevate or grant privileges. The hosted job uses the same entry point, read-only repository permission, a standardwindows-2025 runner and an8-minute limit, without package installs, caches or artifact uploads. Inspect result.status=PASS and all8case outcomes rather than infer correctness from a green badge.

## Limits

This is the existing read-only ACL check on a disposable copy in native WindowsServer2025. It does not qualify a Windows11 interactive installer/UAC flow, real installed Atlas/wallet binaries, all possible ACL policies or a release. It does not repeat repchic's code-page/rights matrix. The older-source comparison uses the same owner fixture but establishes only the missing ownership check, not other baseline behavior.

SHA256SUMS.json identifies supplied bytes. There are no credentials, model files, product changes or private workstation logs. Native job paths/account SIDs in observations belong to the disposable hosted runner.
