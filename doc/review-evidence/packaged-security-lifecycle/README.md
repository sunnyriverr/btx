# Published Linux package — security lifecycle and consolidated acceptance

**Maintained security lifecycle PASS on untouched archive796b9edd, source2f3b5748.** This closes the installed functional-test omission explicitly recorded in Numair’s432comment6704382408. No test repeated for publication.

## Exact new result

[Native run42433202933](https://github.com/sunnyriverr/btx/actions/runs/42433202933), fixtured859714193150457815e2a32f6b85c89f3b65ae4, Ubuntu24.04 x86_64 disposable regtest. Unchanged maintained `feature_model_security_v2.py`, SHA2568cdf2bb75743e27ccf46e489ea25d4edfc6924a7afe4bd46dac688160ccc01bf, exit0/no skip; wrapper PASS. Embedded service status/journal/refusal/pause checks, changed guard boot identity, paused state and valid journal after restart, and responsive ordinary monetary RPC passed. This is a real packaged node/guard lifecycle, not merely the component suite.

Archive asset721231861,158893566bytes,SHA256796b9edd064272b1f443cf3e08646565936183f9f1e15339cad60e84e1014b32. Source2f3 mapping comes from the published replacement description, not an independently reproduced producer build. This is not an execution of later release headff5f3f04. Distributed binaries were used without overlays or source builds. Equality of128 package file hashes was asserted before/after; records retain the before manifest and equality flag, not a separately reconstructed after manifest. Normal shutdown, no cleanup signals or remaining owned processes, runtime removed.

[Exact command/results](records/result.json), [maintained test log](records/maintained-security.log), [verification](records/verification.json), [artifact authentication and file hashes](records/collection.json), [manifest](manifest.json). The executed command is the maintained-security entry in result.json; its config points at distributed binaries. Evidence retains only logs/config/provenance, not wallet data, cookies, databases or private keys.

## Consolidated boundaries on the same archive

| Boundary | Result / existing handoff |
| --- | --- |
| Node-owned guard/helper startup and ordinary restart |59check PASS; [already delivered](https://github.com/btxchain/btx/pull/432#issuecomment-6715089337) |
| Same-host automatic acquisition and publisher departure |Maintained transfer PASS; original wrapper failed afterward and was repaired offline; [already delivered](https://github.com/btxchain/btx/pull/432#issuecomment-6715222615) |
| Embedded security lifecycle through restart |New result above, native test and wrapper PASS |

These are separate runs, not a continuous soak or all-green combined CI campaign. Earlier reports retain their exact limitations. Numair acknowledged startup/transfer; that is not an independent rerun. The original published archive remains unchanged. Its separately discovered Atlas compatibility failure and proposed packaging correction are recorded in [PR440](https://github.com/btxchain/btx/pull/440); this lifecycle pass does not qualify that candidate.

## Limits and decision

This supports the documented security RPC/pause/journal/restart path on this specific Linux package. No protected model workload, full-store recovery, broad authority-policy matrix, GPU, second organization, physical-host deployment, complete suite, absence-of-backdoors or release qualification. Existing component results and the earlier source-built lifecycle remain separate evidence.

Next: maintainer can record this specific packaged functional boundary as exercised. Further execution should respond to a concrete failure, relevant artifact/source change or named missing acceptance requirement. No product change is proposed by this result.
