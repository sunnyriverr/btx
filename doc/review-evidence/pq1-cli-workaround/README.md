# PQ1 external OpenSSL prerequisite — Mac workaround qualification

**Existing BTX_OPENSSL override passes the scoped current-source handshake check; original Linux report remains unverified.** Investigates Jarek’s #432 comment6719123625. No product change, skip or relaxed handshake assertion.

Source release-0.34.16 `ff5f3f04ea11f044594987fc6be043ff68b136ad`. The fixture generates an ML-DSA44 certificate with an external CLI before constructing PQ1 contexts. A newer linked libssl does not select that CLI. `OpensslBin` accepts BTX_OPENSSL; current doc/build-unix.md:73–98 documents the matching OpenSSL3.5+ executable requirement.

## Executed result

Mac arm64, linked Homebrew OpenSSL3.6.3. Compiled current transport_pq.cpp, exact extracted runtime selection/init functions and two unchanged maintained Boost test bodies. The small adapter supplies filesystem/path helpers instead of the full chain fixture. This is **component execution, not test_btx or a complete native node build**.

| CLI selection, same binary | Result |
| --- | --- |
| /usr/bin/openssl (LibreSSL3.3.6) | Intended certificate-generation failure; handshake not reached |
| BTX_OPENSSL=/opt/homebrew/opt/openssl@3/bin/openssl (3.6.3) |12/12 assertions pass: actual TLS1.3, MLKEM768, TLS_AES_256_GCM_SHA384 handshake plus hybrid-peer refusal |
| Invalid explicit CLI | Intended setup failure; no silent fallback |
| Override absent on this Mac | Existing discovery succeeds; same12 assertions pass |

[Raw logs and result](native), [extraction hashes](native/extraction.json), [source test](modelnet_tests.cpp), [runtime source](pq1_runtime.cpp), [file identities](manifest.json). Local workspace paths are replaced with $WORKSPACE; original and published hashes are recorded. No keys or certificates retained. Binary SHA2566d2a050b23026ea0ee898fe4c65d5d7685f6281421f62c356dec3b042cb4e808; actual loaded libraries are in native/result.json. Build used clang++ C++20/O1, Homebrew Boost/OpenSSL headers and matching ssl/crypto libraries; compiled test.cpp, runtime-extract.cpp and unchanged modelnet/transport_pq.cpp. Source preparation/run scripts are retained for inspection, not a claim of a portable full-tree runner.

## Linux verification still needed

Use the existing Ubuntu22 test binary and matching OpenSSL3.5.9 prefix from the reported build:

```sh
BTX_OPENSSL=/path/to/matching/openssl-3.5.9/bin/openssl \
  /path/to/test_btx --run_test=modelnet_tests/pq1_handshake_mlkem768 --log_level=all
```

This Linux command is proposed, **not executed here**. Confirm that this selected CLI exposes ML-DSA44/ML-KEM768, certificate setup succeeds, and the unchanged test reaches and passes its strict handshake assertions. Retain any failure after setup rather than treating the override alone as success.

The local failing CLI was LibreSSL, not Ubuntu’s OpenSSL3.0.2; the local successful backend was3.6.3, not the reporter’s static3.5.9. No Linux/full-unit/CUDA/package/release qualification follows. The next decision is whether the supported environment override resolves the original report; no product repair is established.
