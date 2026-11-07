# Windows S3 socket cleanup: native before/after evidence

**PASS for the focused cleanup repair `ad7ad5cf`; full Windows acceptance remains open.**

S3 transport calls CRT `close` on Winsock sockets in five cleanup paths. The original native failure was localized at `ConnectTcp` line457 with a valid Winsock stream immediately before the call. The repair uses `closesocket` on Windows and retains POSIX `close`, existing branch/error behavior, endpoint restrictions and credential/file-permission checks.

## Result

| Maintained case | Before | After |
| --- | --- | --- |
| `cloud_real_http_socket_cleanup` | CRT abort/201 | PASS12 assertions |
| `cloud_tls_handshake_socket_cleanup` | CRT abort/201 | PASS12 assertions |
| `cloud_https_not_stub_error` | prior exact cached-binary abort reused | PASS7 assertions |
| `cloud_https_use_fake_false_error_is_not_stubbed` | prior exact cached-binary abort reused | PASS15 assertions |

The two new tests are identical before/after; only `s3_client.cpp` changes between their native trees. HTTP transfers exact binary bytes and requires the server to observe clean client EOF while keeping its own socket open. The TLS control accepts TCP, sends plaintext, verifies handshake refusal and requires EOF or a specifically classified reset. No successful TLS/certificate/cloud-service transaction is claimed. Six case invocations in this run; the19 already-passing cloud/R2 cases were not repeated.

## Executed inputs and entry point

- [Native run42348955391](https://github.com/sunnyriverr/btx/actions/runs/42348955391): Windows Server2025 x64, clang-cl20.1.8, MSVC14.51/SDK10.0.26100, static CRT/OpenSSL3.5.4, Modelnet/wallet/ZMQ/tests ON, GUI OFF.
- [Exact executed workflow/controls](https://github.com/sunnyriverr/btx/tree/636055d4621714a5d7cba3a05c5c8ae23fbb4a5e/contrib/devtools/windows-root-configure) and [workflow](https://github.com/sunnyriverr/btx/blob/636055d4621714a5d7cba3a05c5c8ae23fbb4a5e/.github/workflows/windows-root-configure.yml). `socket_repair.py baseline`, `build`, `run`, `retain` are the executed stages after verified cache restoration. This is a retained-cache recipe, not a clean full-build reproduction.
- Product proposal: `ad7ad5cf6cd53a230af1a9de7bb4532d5d48f582`, parent `d522af520f55067bd470fdcc0c246e3b4d3a26fc`.
- Native before: `d5d74b212cd2a38f2f2b0c9c17154404090f2a3f`, binary `5005eb3716338d51a1da78d581bceac0c41907ec90ac22bf51d483d01a80760d`.
- Native after: `c660512641edf3bfb36f287e56a6fa0a8794fe64`, binary `f13fb9c3c768f1b80ca913dc6fcdc60f3c6a94786a0e715cf90d347434dfc843`. This evidence branch descends from that exact tested source. Product S3 bytes and the two new test helper/bodies match the proposed branch exactly.
- Existing refusal baselines: [run42235419798](https://github.com/sunnyriverr/btx/actions/runs/42235419798), unchanged4ca source/binary89ec. The two cases now pass on the uninstrumented repaired binary; they were not re-run as new before controls.

After a supported normal project build, the new in-tree regressions can be selected individually:

```text
test_btx.exe --run_test=modelnet_cloud_tests/cloud_real_http_socket_cleanup --log_level=message
test_btx.exe --run_test=modelnet_cloud_tests/cloud_tls_handshake_socket_cleanup --log_level=message
```

Actual native arguments, exit codes, durations and log hashes are in [commands.json](commands.json). Raw case [logs/XML](logs), [verification](verification.json), [profile](profile.json), [source/provenance](provenance.json), and [file manifest](manifest.json) are directly readable here. The two builds took20.39seconds (test-only) and10.62seconds (repair); all5885 object paths were retained, with only the two changed CPPs and planned metadata consumers rebuilt. Metadata application relinks are disclosed, not counted as node runtime qualification.

## Prerequisites and remaining gate

Native execution used the maintained pending Windows prerequisite integration atop666, including cloud/R2 ENV credential fixtures; it was not a stock d522 build. The original S3 file is byte-identical in that cache, d522 and the reviewed0.34.16 release. `provenance.json` lists the31-file integration/current-base difference; source ancestry and patches retain all prerequisites. No product credential/endpoint/permission check was weakened. The two new tests use synthetic ENV credentials and a local ephemeral port, independent of the pending PATH-fixture correction.

**#356 still requires a full native Windows node build and maintained unit run on requested `d522af52`.** Current-source prerequisite/configuration reconciliation and that full run are unfinished. This result does not qualify the release, Windows installer, full suite, Linux/macOS execution, production node/helper, successful cloud/TLS operation, full-width socket handles or native timeout behavior. Immediate-connect and wait-failure branches were not individually forced. Existing int handle representation and timeout ABI are unchanged. Owned server/runtime/process cleanup passed; original and repaired caches were preserved.

Credit for preceding native Windows findings and build/fixture review context: [repch1c](https://github.com/repch1c) and [Jpp-matata](https://github.com/Jpp-matata). Original source authorship/copyright/history remains intact. No independent human ACK is inferred from internal review or the contributor names.
