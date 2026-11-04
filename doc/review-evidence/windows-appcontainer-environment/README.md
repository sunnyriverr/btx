# Native Windows AppContainer environment repair

**Same native finite-tool test fails on accepted `ecd9310a` and passes with `2c954125`.** One Windows-only file, nine additions. Only LOCALAPPDATA joins the explicit child environment; missing/empty/incomplete retrieval refuses before profile allocation. Capabilities, token/Job checks, handle allowlist, limits, private TEMP/TMP and output verification stay unchanged.

Product `2c9541253fc1d8f484ec8725eb91f283b148b7d5`, tree `984f8da23c8be7b0d7595ada1d727f9820e91508`. [Code branch](https://github.com/sunnyriverr/btx/tree/codex/fix-windows-appcontainer-environment). Related inventory: [repch1c’s #338](https://github.com/btxchain/btx/issues/338); thanks to Numair for native qualification direction. This does not resolve #338’s in-run tree/combined-CPU accounting or close #356.

## Executed comparison

[Native run41819388079](https://github.com/sunnyriverr/btx/actions/runs/41819388079), CI commit `e67bbea628f84404d61a3e3a19c02ac3a3043598`. Windows Server2025 x64, MSVC14.51.36231, C++20 Release/static CRT. Actual Windows backend, confinement/filesystem-jail wrappers and SHA384, with root-derived relevant flags and separate build directories. Same unchanged driver/helpers/dependencies for both source versions; no API shim or injected environment. No full Modelnet/node library or shared cache is used.

| Case | Original | Repaired source |
| --- | --- | --- |
| Same finite tool/driver | JAIL_ABSENT; no launch/output | JAILED; child0; exact512 output bytes |
| Direct backend classification | WINDOWS_SANDBOX_CREATEPROCESS | Supported wrapper succeeds |
| Original helper/input digests | preserved | preserved |
| Parent-sentinel exclusion and OS value present | tool cannot start | valid-control helper passes |
| Required parent value unavailable | not part of this paired control | WINDOWS_SANDBOX_ENVIRONMENT; no launch/output |
| Fresh normal invocation after refusal | not claimed | passes |

[Result](native/result.json), [executed commands](native/commands.json), [source/fixture/pre-test binary identities](native/identities.json), [artifact hashes](native/collection.json). Baseline nonzero exits are expected and asserted; the comparison job passes. The final uninstrumented run records a CreateProcess-stage refusal, not numeric error203; that numeric code was observed only in the earlier diagnostic.

## Reviewer entry point

Use a disposable native x64 Visual Studio Developer Command Prompt with Python3. The exact executed entry point, available at the CI commit above, was:

```bat
set "CL="
set "_CL_="
python contrib/devtools/windows-environment-repair/run.py
```

The executed [workflow](fixture/workflow.yml) preserves checkout bytes and sets up the VS environment. Its runner verifies source bytes, builds both real versions, saves binary hashes before tests, interprets expected failures, performs controls, owns cleanup and exits nonzero for an unexpected result. It downloads no project dependencies.

The byte-identical fixture is included here for a reconstruction from the product checkout: copy `fixture/` into `contrib/devtools/windows-environment-repair/` and run the command above from that checkout’s root. The workflow is stored alongside the evidence for inspection; copy it to `.github/workflows/windows-environment-repair.yml` only if explicitly setting up your own CI. This copied-path reconstruction was not rerun for publication; the immutable CI entry point was executed. Generated results go into a separate windows-environment-results directory.

## Limits and preserved behavior

External standalone component test, not default test_btx or full root-CMake/node/cap02 CLI qualification. Windows11 and clang-cl remain untested. Linux/macOS are source-unchanged behind the existing Windows guard; they were not rerun. The actual successful path verifies its zero-capability/low-integrity AppContainer and Job before executing the helper; no separate escape or complete sandbox-security qualification is claimed.

One existing C4267 conversion warning remains in both builds. Owned fixture roots were removed and no new matching btx.native.* directories remained; this is directory observation, not complete profile-registry enumeration. Missing/empty/growing-value bounds are source-reviewed; only missing-value refusal is exercised natively. Fresh recovery uses a new invocation/root. Binary identities are retained as hashes; executable downloads and reproducible-build claims are not offered.

The earlier API-seam lead and setup pilots are excluded from this current product proof. [Product patch](product.patch), [identity summary](identity.json), public-copy provenance and MANIFEST.json bind this package. Raw Windows CI workspace/compiler paths are retained because they identify executed commands; no operator credentials or wallets are included. Ordinary publication bookkeeping is omitted from the identity summary.
