# #505 Linux identity-list recovery

The same real-helper Unix RPC fixture exposed a false success before the fix and verified recovery after it.

| Case | Original #505 | With checked JSON replacement |
| --- | --- | --- |
| Injected 5,781-byte file limit during identity-list save | RPC reported success, list became invalid JSON, one extra key remained | RPC returned IO, both old entries and key files stayed byte-for-byte intact, and the newly created key and temporary file were removed |
| Retry and clean restart | The existing list was unreadable after the failed save | A healthy retry added one identity and complete key. Both old identities and their keys, plus the new identity and key, survived restart |
| Cleanup | Helper stopped and disposable files were removed | Helper stopped and disposable files were removed |

Ubuntu 22.04, GCC 11.4. Both helpers relinked the changed object at `-O0` with the same verified `dac9aee5` release cache. The fixture uses a process file-size limit, not a physically full disk. The full suite, other shared-writer callers, concurrent updates and macOS/Windows were outside this run.

- Author head `149ebe08e9f724754ba68b69e6d7fa71148647f3`
- Tested product tree `0003a0db9bcaf28b83fb9bd830f4f6dbd412c1ac` and [cherry-pickable fix](https://github.com/sunnyriverr/btx/commit/919d69dafbcce756d288b9b5e5f4b59834aa9919)
- Baseline helper SHA-256 `3980a88bbd80eb67023174ddf8404e34d73eefdcc1f1e684c4c14794cc1f5938`
- Candidate helper SHA-256 `5f122ae321c34e17afb0b05ecb69a8c168378c78dd2e288d59b8a64f57cbf373`

[Executed CI and artifacts](https://github.com/sunnyriverr/btx/actions/runs/42996863295) · [Fixture](https://github.com/sunnyriverr/btx/blob/8c206b60934b8a5b594e401720acc82df5c9a880/native_fixture.py) · [Pinned CI recipe](https://github.com/sunnyriverr/btx/tree/8c206b60934b8a5b594e401720acc82df5c9a880)
