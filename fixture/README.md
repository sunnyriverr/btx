# Native settings fixture

Prepared only; no compile or native execution performed by this subtask.

`helper-retry-restart.py --helper <exact binary> --channel-fixture <channel.json> --out <logs-dir> --expect baseline|candidate`

Five real-helper cases: direct rejected watch creation; rejected watch replacement through deterministic mirror KEEP watch; signed channel creation/replacement; rejected operator-policy save. Every case uses a fresh disposable helper store and private Unix socket. `getmodelwatchactions` always uses `drain:false` and expects an empty queue; no downloads, wallet/node or peer listeners are configured. Each process stops cleanly, then restarts on the same disposable store. Calls and logs are retained; private keys are never emitted by the signing utility or copied out of the helper scratch root.

- Baseline expects each of the five product contracts to fail while setup, unchanged saved bytes, error results and unrelated-state controls remain strict. Candidate requires all contracts to pass.
- Direct watch RPCs do not take an explicit watch ID, so they cannot replace an existing watch. `setmodelmirror` provides the supported deterministic replacement. Its existing partial mirror/watch-save semantics are not redefined.
- Mirror's same-key failed idempotency result is intentionally cached. The fixture verifies that replay and then uses a fresh idempotency key with identical selector/keep settings. This is not labelled an identical-key retry. Direct watch and signed-channel retries use identical payloads.
- Policy startup intentionally re-applies launch flags and rewrites policy.json. The fixture proves saved bytes before shutdown, verifies the known launch reset, and reapplies the ordinary policy after restart; it does not promise policy overrides launch flags.
- `channel-fixture.cpp` uses production GenerateMlDsa44/SignSignedChannel/VerifySignedChannel and resource URI encoding. It emits genuine unrelated and target sequence1/2 payloads including public key/signature, because SignedChannelToJson omits those wire inputs. The disposable secret key is memory-cleansed and never output.

Build the signing utility with the restored source/build include paths and normal modeld static-library/link dependencies, replacing modeld.cpp's main object with this utility object. It includes generated bitcoin-build-config.h, modelnet identity/model_watch/resource_uri headers, span via those headers, support/cleanse.h and util/strencodings.h. Capture exact compiler/linker command and binary SHA before using it. Do not change production code for fixture access.

Total native case loop is bounded at180s, each RPC10s, each helper startup30s and shutdown15s (+5s forced cleanup). The parent should impose a hard outer timeout (e.g.300s) on the entire subprocess as well; a synchronous case can consume its own request bounds before the total loop rechecks. Native runtime remains unverified until the parent executes this exact fixture.
