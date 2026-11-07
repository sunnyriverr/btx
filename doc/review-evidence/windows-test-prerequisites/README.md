# Windows test prerequisite fixes

**31/31 selected native Windows cases PASS on `37472d88`; full Windows unit run remains incomplete.**

Proposal `d90333b9d3cff45424431f96d4cabdd4a36ce4fe` targets `release-0.34.16` at `2f3b574867c11ab79eba829123689b76e6137a38`. Two atomic commits change only configured helper paths/dependencies and scoped positive cloud/R2 credential fixtures. Its three file blobs exactly match the tested integration. Original source and Windows audit/review credit to repch1c and Jpp-matata are preserved.

## What ran

[Native run42413581374](https://github.com/sunnyriverr/btx/actions/runs/42413581374), Windows Server2025x64/clang-cl20.1.8, Modelnet/wallet/tests/ZMQ ON, GUI OFF. Normal maintained build links all seven targets in41.59s; correct-flags cache reuse preserves5885objects with zero command changes. Selected tests take75.70s.

- Four suffix-less helper-path failures and21 cloud/R2 credential failures from prior run42373148335 now pass. The prior native failures were reused by source/binary/XML/log identity rather than rerun.
- Six controls pass: ENV restoration2, actual modeld parser/btxdhelp1, btx-open failclosedJSON with validcore-v1control1, nativeconfine/fsjail helper execution/cleanup2. Exact selectors are in [selected-cases.json](selected-cases.json).
- Unsafe credential-file refusal, POSIX PATH branches, distinct read/write keys, redaction and operation assertions remain intact. Tests use synthetic credentials.

## Exact scope and prerequisites

The executed source is d522 plus six separate fixture-portability corrections, adopted #433 and these three fixture/configuration files. The six prerequisites are listed by file/blob in [manifest.json](manifest.json) and included in [tested-integration.patch](tested-integration.patch); they are **not** part of this three-file proposal. The evidence branch retains `37472d88c1e0d7dd88ac92e1c698351a0a7e9bd7` as an ancestor, so that exact tested source is available as a commit.

The proposal base already contains #433, whose S3 code and two cleanup tests are not duplicated. The two previously masked nonfake transport results are combined-prerequisite evidence, not proof that ENV fixtures alone repair sockets. The before campaign used suite batches; this campaign uses isolated selected cases and fresh short test roots.

Only31 of15388 registered cases were selected here. The earlier broader campaign had other failures, a timeout and unrun cases. **This does not close #356.** The full proposal/release tree, full Windows unit run, cl.exe, Windows11 desktop, POSIX runtime and release-wide acceptance are not qualified by this result.

## Reviewer entry point and raw evidence

The actually executed entry point is [the workflow at controller02aeb844](https://github.com/sunnyriverr/btx/blob/02aeb8448f7d10f6246812a8474224b25a2d951f/.github/workflows/windows-root-configure.yml): exact cache/profile restore, normal currentconfigure/plan, maintained build, checkpoint, explicitcase runner, cleanup and scoped verdict. It requires the recorded immutablecache; no fresh clean-build replay of the published branch is claimed. Exact executed controls are in [controls/](controls/).

[verification.json](verification.json) records each of the25 before/after case outcomes. [result-review.md](result-review.md) independently checks the native raw result. Unmodified case logs/XML are in [before/](before/) and [after/](after/); build/configuration/import/inventory logs are in [native/](native/). All payload hashes are listed in [evidence-sha256.json](evidence-sha256.json). Full native artifactSHA256 is `8338efefbaaf1fefc731a82c700d70942a87287cabd99118fdf4865c8ed4544f`.
