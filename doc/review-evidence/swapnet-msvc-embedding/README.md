# SwapNet frozen bootstrap: native MSVC acceptance

**Tested ACK 371013d6 — frozen-bootstrap generator only.** Numair's existing repair reproduces fail-before/pass-after with the compiler used in bs1812's Windows report on upstream #714.

| Matched input | Result |
| --- | --- |
| Old generator from `1e2f8b5f12295002334d3390c12cac0bb4ae2aff`, current package payload | `C2026: string too big, trailing characters truncated`, compiler exit2 |
| Current generator from `371013d61dc124a363521df5b94e97f64d2464f2`, same payload | Compile0, executable0, byte-for-byte correct payload |

Native x64 MSVC 19.44.35230, preinstalled toolset 14.44.35207, Visual Studio 2022 Enterprise 17.14.37906.3 on hosted Windows Server 2022; SDK10.0.26100.0. Python 3.11.9/defaultcp1252. C++20, `/utf-8 /EHsc /O2 /MD /Zc:__cplusplus`.

Both generators receive the same current Python package, isolating the generator change. Before emits one 300,866-character raw literal; after emits38 literals, maximum 8,000characters. The candidate executable writes300,866bytes, SHA256 `893d6dd0b4715b771e1cbda544960d9f4cb350d9440979dfae65856fae997206`, exactly matching the reconstructed expected payload.

## Executed evidence and reproduction

[Passing run43976871719](https://github.com/sunnyriverr/btx/actions/runs/43976871719), executed CI commit `490c6c4f7ff017039efa73489686f87dd545069d`; [actual workflow](https://github.com/sunnyriverr/btx/blob/490c6c4f7ff017039efa73489686f87dd545069d/.github/workflows/swapnet-msvc-probe.yml), [actual probe](https://github.com/sunnyriverr/btx/blob/490c6c4f7ff017039efa73489686f87dd545069d/contrib/devtools/swapnet-msvc-probe/probe.py). Production sources are pinned371013d6; the CI commit changes only the probe/workflow. On a Windows machine with the named preinstalled compiler, the executed command is `python contrib/devtools/swapnet-msvc-probe/probe.py` in that CI tree. The probe inventories installed compilers and requires19.44; it never installs or falls back to another compiler.

Probe 12.578seconds; complete hosted job 30 seconds;20-minute cap. Artifact 14280738793 contains generated headers, compiler logs, consumer sources/objects/executable, and expected/actual payload. ZIP SHA256 `921d17c696bbde61baa873d5a6dc8fd121d08d85be8da5199cecf82918b7129a`. Adjacent `result.json`, compile logs and `artifact-receipt.json` preserve identities and results; `probe.py` is the exact executed probe. Artifact retention 14 days; the small text evidence here is durable.

A prior MSVC19.51 run43961721025 passed both old and current generators. It is a newer-compiler control, not fail-before evidence. The matched19.44 run uses identical generator/source hashes and candidate output, all checked against that retained result.

## Scope

This is a native compiler/minimal-consumer execution check of Numair's generator repair, not a whole-old-tree versus whole-new-tree build. It does not qualify the full Windows node/unit build, Python runtime imports/dependency installation, funded swaps, or a release. Windows Server 2022 differs from the reporter's Windows 10 PC; compiler/toolset/VS release match. No product patch was needed. Credits: bs1812 for the original Windows report; Numair for the existing fix. Probe and report prepared with AI assistance; native results are from the linked run.
