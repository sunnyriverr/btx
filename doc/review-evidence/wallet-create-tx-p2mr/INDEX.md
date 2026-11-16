# P2MR wallet transaction checks: verified evidence

One Ubuntu 24.04 x86_64 comparison, source1e2f8b5f, unchanged retained btxd/CLI, no rebuild. Original passed locktime then failed unsupported-address setup; draft passed all five methods. This repairs test compatibility, not product code.

- [Outcome and full limits](README.md)
- [Verified provenance receipt](qualification-receipt.json)
- [Original/draft results and cleanup](comparison.json)
- [Original methods](original-methods.json) / [draft methods](draft-methods.json)
- [Original log](original-functional.log) / [draft log](draft-functional.log)
- [Test-only patch](test-only.patch)
- [Comparison manifest](manifest.json), [method observer](run_case.py), [bounded driver](run_pair.py), [workflow](workflow.yml)
- [Static source/binary/dependency verification](verification-result.json)

Scope: harness-assisted direct functional framework/shared initial CPU profile. Original restart semantics retained, draft preserves its profile. Not standalone or normal test_runner launch, Mac/Windows/full suite/production. JPP774's observation and prior P2MR chain evidence credited. No tests repeated to publish.
