# Mirror wrapper request-key correction — native evidence

**Qualified2f9e585e:** the same maintained mirror regression fails with the original wrapper and passes with the correction. Helper idempotency and zero-spend checks are unchanged.

Code2f9e585e4e11116c94e71feb8dcf2e8d5b41d2f0 on accepted666673a3153225ba264c7870e0e82e354df86765. Three files: wrapper, maintained profile test, mirroring docs. Original source headers retained; Sunny River prepared the correction and Codex-assisted test tooling.

## Behavior

A new mutation gets one fresh128-bit token before its RPC call. --idempotency-key preserves an explicit caller key for retries. Blank keys or a key without a mutation are rejected locally. Plain inspection still uses getmodelmirror. Helper mandatory-key, cached replay, fingerprint conflict and nonzero-spend checks are unchanged. The cache is process-local; no restart-persistent replay guarantee is added.

## Actual before/after

[Native run42192725966](https://github.com/sunnyriverr/btx/actions/runs/42192725966), execution fixture1647dbee1e3dd0cb7d75dca95b7702cdae0dbc70. Ubuntu24.04 x86_64, accepted666real node/CLI/helper and real Python wrapper, disposable empty wallet-disabled regtest. The exact final maintained test_mirror_cli body is identical in both variants.

|Check|Original wrapper|Corrected wrapper|
|---|---|---|
|Default mirror update|Refused: idempotency_key required|Requested selector saved; unrelated selector retained|
|Focused maintained method/process|Fail/exit1|Pass/exit0|
|Explicit-key same-body replay|Unreached|Success; preserves bytes and deliberately old filemtime, proving no rewrite|
|Changed arguments with same key|Unreached|Conflict refused; policy unchanged|
|Read-only inspection|Unreached|Success; no rewrite|
|Empty/key-only option|Unreached|Exit2, no saved change|
|Direct missing-key/nonzero-spend controls|Unreached|Each refused for its specific reason; policy unchanged|

The method is registered inside existing feature_swarm_profile_overrides.py. Qualification executes this exact new method through a focused external-helper adapter; the whole existing profile script and default-owned helper lifecycle were not rerun. No baseline assertion was weakened. Local Python probes separately establish distinct32hex-character default keys across invocations, explicit-key forwarding, read-only routing and pre-RPC invalid-option refusal.

## Exact inputs and execution recipe

Source-manifest.json and candidate.patch identify final code; candidate/ contains the exact qualified wrapper/test/docs. Native-verification.json records same-method hash, exits, binary identities and cleanup. Records/ contains raw observations, logs, config, run metadata and digest-verified artifact manifest.

Native node SHA2564ad63b64f6d6bab34f5ba92518dc8955ee2e263e0daa4d739f27ec868fce0ae1 and CLIb71061e57a9224d86ef2f17da1914f3b68ffe91b696282151c0aba9e12caa5b8 were reused from immutable cache10096149671. Only unchanged helper target was rebuilt from retained inputs (5.976s), matching62e2a47bb52507615129820aeda4e54aeac4d8744419d12833ffa148dbc88df3. No node/CLI rebuild or cache save. All14,309original source bytes/modes restored and all three binary hashes unchanged after the pair. Pinned OpenSSL and CMakeCache identities verified before reuse.

The executed recipe is native-workflow.yml plus native-run.py/native-case.py/native-expected.json, at the original contrib/devtools/mirror-wrapper-repair paths in the fixture. Exact invocation and durations are in records/result.json. Candidate-wrapper.py and candidate-test.py at those fixture paths correspond to candidate/contrib/modelnet/btx-model and candidate/test/functional/feature_swarm_profile_overrides.py here. These are preserved executed scripts; restoring the original layout/cache is a reconstruction prerequisite, not a promise that another account can access the branch-scoped cache. No fresh full-build recipe is claimed executed.

Artifact13490760684 SHA256bb34258292d1c2fccd34234e3a709908ccc0a3f4f6865e06780f44a152f2f56b was checked before retaining198,920expanded bytes as readable records. These records do not depend on the runner artifact surviving its retention window.

## Cleanup and limits

Two normal helper exits0, explicit node RPC shutdowns, no runner fallback signals/survivors, temporary runtime removed. The temporary candidate wrapper replacement was restored before final source audit. No production/wallet/model/cloud state touched.

Runtime node Modelnet disabled; external helper Unix RPC only, no peers/models/mining/funds. This is not native Windows/macOS integration, the full profile script/fullsuite, default-owned helper or restart qualification, concurrent-update proof, GPU/network/model acquisition or release qualification. The separate node btx-cli profile/mirror object-conversion findings are not fixed here.
