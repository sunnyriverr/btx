# Serialize default publisher creation

The real helper reproduced the lost update when default publisher creation paused after reading the list. Both calls succeeded, but only the default identity was listed. With the same forced overlap, explicit creation waited and both identities and full key files survived restart. Ordinary serial creation passed.

Ubuntu 22.04 helper RPC with a controlled read pause and disposable keys. Cross-platform and broader concurrency coverage are outside this run.

The shared workflow is marked failed because the separate #494 bundle fixture stopped at request validation. The published #504 results are in its own successful section of the artifact.

The matched run uses the verified `dac9aee5` checkpoint and GCC 11.4. Changed translation units were compiled at `-O0` in both variants. The patch builds on repch1c’s original changes.

- Author head `b21ca36b961f52331b226f58a51aa45da99ecb67`
- Tested product tree `8e989d24daae5ff4f4f177c6811738aab9662aee`
- [Cherry-pickable fix](https://github.com/sunnyriverr/btx/commit/25a5fc03a4c4f2927646c1dcc6a122455ea3cd0e)
- [Executed CI and per-PR records](https://github.com/sunnyriverr/btx/actions/runs/43000822596)
- [Pinned fixture and build recipe](https://github.com/sunnyriverr/btx/tree/8bab7fdc0f8ff360b0e0e74b84eb2a60a0c41d5c)
