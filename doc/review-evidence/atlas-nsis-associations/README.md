# Atlas NSIS association lifecycle: installer evidence

**Fix 95e24727 preserves the previous .btx handler across same-version reinstall and preserves a later different handler on uninstall.** The same actual-package acceptance script fails in those two cases on Atlas e70c81f0 and passes after the repair. Normal single-install restoration passes on both sides.

Product branch: [codex/fix-atlas-association-lifecycle](https://github.com/sunnyriverr/btx/tree/95e24727b3a2378cef3c668b919f0415e1fe38c5); base `btx-035/atlas-native` at `e70c81f03b76c5e62712ebb51dfaac7d41295af2`. Three changed files, one commit. The generated installer is retained: an NSIS hook overrides only its association helpers. Missing/empty or legacy self-referential backups remove only the Atlas-owned default; the fix cannot reconstruct a handler already lost by an older installer. Later selections and unrelated extension data remain intact.

Credit: [repch1c's original installer report](https://github.com/btxchain/btx/pull/273#issuecomment-6445929206); derived helpers retain Saivert/Nikku attribution and the upstream Tauri MIT/source notice. This is installer work associated with #273, not a request to close that Atlas PR.

## Exact identities and results

| Actual installer case | Baseline | Repair |
| --- | --- | --- |
| Install `/S /NS`, uninstall `/S` | Prior handler restored | Prior handler restored |
| Same installer twice without uninstall, then uninstall | Default references deleted Atlas class | Prior handler restored |
| Install, select later handler by registry, uninstall | Later selection overwritten | Later selection retained |

All 139 ordinary identity, process-completion, preservation and cleanup assertions pass on both sides. These are assertions across three workflows, not 139 application tests. Raw [baseline](baseline/result.json) and [repair](candidate/result.json) include registry snapshots and installed-file observations. The same script is [recipe/run.py](recipe/run.py), SHA-256 `60802feef8b830f52e6bb9f40ed05284cf1405a1184c31a50b4d86fda01e4850`.

- [Baseline native run41985452016](https://github.com/sunnyriverr/btx/actions/runs/41985452016), CI `9e295032f6e64e6f18b001edd81e4e2eaf1765ab`. Installer SHA-256 `8df000ba197a46417dac4887bf895928feda08c00bb7453057bac9586968a8ac`.
- [Repair native run41988968998](https://github.com/sunnyriverr/btx/actions/runs/41988968998), CI `389a9d04dcf273a317dde4256e4358f68c6e6c88`. Installer SHA-256 `4d9362f7103fed31ff4877979485a079259ff799fcdd5634796cc14ccaa34fbc`.
- Tested code `8b3a586085a31af68c74696fafffb1b540c04132`, full tree `409a748829cd0b525fe4d09248c6a7321cfd4e58`. Published code `95e24727b3a2378cef3c668b919f0415e1fe38c5`, tree `51a0eb3abfd9baeadbaf849c09e02820a36bea80` differs only by leading license/source comments and commit metadata. [Exact mapping](identity/header-only-mapping.json): runtime macro body is byte-identical; config and maintained-test blobs unchanged. No additional native run is claimed for the comment-only amendment.
- Candidate checkout requires the full tested tree and hashes all 230 Atlas source files before/after packaging. [Bundle audit](candidate/bundle.json), [qualification](candidate/qualification.json), [input catalog](recipe/product-inputs.json), [tested patch](recipe/product.patch).

## Maintained regression and reproduction

The product adds `gui/atlas/tests/nsis_associations.py`, a standalone Windows-native entry outside the default Node runner. Supply Python3 and an installed NSIS3 compiler explicitly; it makes no downloads, uses unique disposable association keys, and does not open real .btx files:

```powershell
cd gui/atlas
py tests/nsis_associations.py --makensis C:\NSIS\makensis.exe --out after.json
py tests/nsis_associations.py --makensis C:\NSIS\makensis.exe --baseline-macros C:\path\FileAssociation.nsh --out before.json
```

Use the pinned vendor `recipe/original-FileAssociation.nsh` for the baseline path. The same eight scenarios exercise prior, repeated, later, initially missing, self-backup, missing-backup, later with poisoned backup, and later-to-reinstall states. Native compilation/execution: baseline 19 assertion failures out of 154 checks; repaired 154/154 pass, no runtime/cleanup errors on either side. These are macro-component scenarios, not eight full application installs. [Comparison](candidate/edge-comparison.json), [before](candidate/edge-before.json), [after](candidate/edge-after.json).

For the actual-package qualification, the exact executed [workflow](recipe/workflow.yml) and [recipe](recipe/) are retained, rather than replacing them with an unexecuted launcher. That workflow uses a fixture layout `contrib/devtools/atlas-association-repair/`, an immutable Atlas e70 checkout and baseline package from run41983707124. The recipe applies the tested patch, bundles, runs the maintained regression and then the unchanged actual-package acceptance script. Follow its explicit fresh-runner/preflight requirements; do not run the real installer recipe on an operator workstation. Reusing it requires the original package artifact (retained until 19 Nov2026); current action artifacts are temporary, while these readable records remain in this branch.

## Packaging and preservation

Windows Server2025 build26100, current-user x64 NSIS, 64-bit registry, NSIS3.13, TauriCLI2.12.4/Rust1.95.0. This is standard `cargo tauri bundle` with the hook, not a hand-edited generated installer. No new Rust application compilation: the original compiled app is extracted and its unique bundle marker reversed to the exact original whole-file hash, then normal bundling patches/restores it. Extracted candidate app and four installed copies match original embedded app `e058b70b7ddcfd28cb05cbf9b051e1598acfaff7bfde0a56e5f455500890d20f`. The same baseline-extracted offline WebView prerequisite is reused as packaging input; this does not independently verify the candidate prerequisite extraction or absent-runtime installation.

Controls preserve unrelated extension values/subkeys, prior/later handler definitions, a manufacturer sibling, Run entry and appdata; HKLM associations and Explorer metadata remain unchanged. Owned protocols/ARP/files are removed and fixture cleanup passes. PowerShell waits for the installer process tree, followed by independent end-state checks; individual child exit codes are not separately retained. No app, node or wallet launch is requested.

## Limits and next acceptance gate

**Windows11 remains unverified:** interactive install/reinstall/uninstall, Windows Settings/UserChoice/default-app selection and actual .btx opening. No Windows10 GUI, upgrade/downgrade, machine-wide install, signing, absent-WebView, full application/unit-suite or release qualification is claimed. Later selection here is direct registry mutation. Third-party rewrites of Atlas's own ProgID and concurrent independent install paths are outside scope.

Baseline setup history is retained in its native CI: the first package run stopped at a BOM/CRLF provenance guard despite successful compilation/packaging; a first installation pilot used an incorrect binary oracle and yields no restoration verdict. Final baseline uses independently extracted installed bytes. Its after-build source audit was not reached; the candidate's before/after audit completes. No repeated candidate campaign is represented.

`verification.json` redacts only the local Mac checkout path; [manifest](MANIFEST.json) identifies original/published hashes. Other copied recipe and native result files preserve their original bytes. Candidate observation archive SHA-256 `b68b74232a6277e6f5a0134432d244a372250f2c668a6636351ec1bb200f8506`; installers stay in native artifacts, not this evidence tree. This evidence branch has no executable GitHub workflows.
