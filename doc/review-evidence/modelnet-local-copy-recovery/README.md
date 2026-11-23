# ModelNet local copy recovery

On Ubuntu x86-64, re-importing an independent verified local copy repaired a same-sized damaged stored piece. The original model could be checked out after reopening the catalog, with both source directories offline. The original model ID, artifact ID, pin, quota and unrelated catalog entry were preserved.

| Result | Stock | With repair |
| --- | --- | --- |
| Exact stored piece | Failed | Passed |
| Checkout after reopening | SHA-384 mismatch | Passed, exact bytes |
| Assertions | 18 executed, 2 failed | 20 executed, 0 failed |

The paired run used the same maintained case in an isolated executable linked to the production ModelNet catalog and store. Source was `d9a9480484cea303649f3eab1e82f8e3d7572c21` with the [attached patch](candidate.patch) applied on the candidate side. The extra assertions on the candidate side check the output file once checkout succeeds. [Fork run and controller](https://github.com/sunnyriverr/btx/actions/runs/45088008763)

[Stock log](baseline-regression.log) · [Candidate log](candidate-regression.log) · [Build and command record](build-result.json) · [Artifact digest](readback.json) · [Maintained case body](maintained-cases.inc)

This was a component run with a simulated local file fault. Full daemon or default test suite, peer transfers, macOS and Windows were outside the run. The repair covers matching indexes and readable, same-sized damaged local pieces. Repch1c's [#934](https://github.com/btxchain/btx/pull/934) covers a separate prevention path.
