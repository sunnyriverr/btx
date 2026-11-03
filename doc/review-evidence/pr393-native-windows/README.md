# PR393 native Windows component evidence

**Baseline fails for the nine expected duplicate symbols; PR393 links and executes successfully.**

- Native run: https://github.com/sunnyriverr/btx/actions/runs/41646082764 (attempt1).
- Exact fork workflow/runner commit:22373c44035249ad74fd5a39e718a9d3c1298aba.
- Baseline:cbf65894e6d61084527cd93e913a00c6794418dd; candidate:d1ee21e828df480d6a3b9605a0d08a21fce8c6ef.
- Original production-file and driver manifest: https://github.com/sunnyriverr/btx/tree/eca826d8040ff222feb5595c18c75193e336c7c4/contrib/review-evidence/backend-stub-ownership . The native runner reads and checks those exact Git objects; no product changes accompany this evidence.

WindowsServer2025 x64 build26100, clang-cl/LLD20.1.8, WindowsSDK10.0.26100.0, MSVCtools14.51.36231. Both revisions compile seven production stub translation units and the same published driver into native COFF objects. Baseline direct/whole-archive links each fail with the nine named CUDA/Metal/HIP duplicate definitions. Candidate direct/whole/ordinary archive links succeed, and each executable passes the12dispatcher/output checks. Baseline ordinary archive was not run. Exactly45commands; only the two intended baseline links exit nonzero.

Start with summary.json and result.json. The flat actions-log.txt preserves the full original downloaded job transcript, including compilation/COFF/tool/SDK evidence. Selected decoded logs remove Actions timestamp prefixes for easy reading. The original downloaded log archive hash is recorded in summary.json; that ZIP is retained locally, not the primary review surface. review.md includes source preflight and final artifact review. This is one CI execution with internal artifact review, not another independent platform replication. Execution/review used Codex.

## Entry point

In a native x64 VisualStudio developer shell with preinstalled clang-cl,lld-link,llvm-lib,llvm-readobj and Python3, and a local BTX repository containing the three exact commits above:

```cmd
python verify_windows_linkage.py --repo C:\btx --out C:\btx-checks\pr393-new
```

Output must be a new directory under an existing parent. CL,_CL_,LINK must be unset. The runner requires nativeWindows/x64 and the disk floor, verifies Git/source/driver hashes, fails on unexpected diagnostics, and writes result.json with commands/exit codes/tool/executable hashes. native-windows.yml records the exact hosted-job environment and execution. It installs no packages and uses no external Actions steps, caches or artifact uploads.

The committed runner LF hash10b995f7... becomes32f61177... under Windows checkout CRLF conversion. That exact byte conversion was independently verified; production inputs come from git show and retain their original byte hashes. The recorded driver hash identifies its extracted source string; native text output uses Windows newlines equally for both variants.

## Scope

This closes the nativeWindows clang-cl/CRT/COFF disabled-backend component gate. It does not establish full btxd linkage, all CMake profiles, enabled GPU providers, MatMul computation, plain cl.exe or release qualification. Earlier Mac enabled-marker and weak-symbol controls remain separate. Credit repch1c for the original Windows failure report in #356. No additional tests were run for publication.

SHA256SUMS.json identifies every supplied evidence file. No credentials, private workstation paths, production data or model checkpoints are included.
