# Saved cloud configuration diagnostics

The same isolated helper regression exited 2 before and 0 after on the release source and on #861. Before the fix, failed load and missing configuration returned identical status. Afterward, the failed load returns a fixed `init_error` without copying paths, file contents or parser text. Missing configuration remains quiet.

Restoring the exact saved bytes reopened the connection without a second `setcloudstorage` call. The local origin returned HTTP 200 for PUT and GET. All variants preserved the damaged configuration and budget through failed load, and each passed six local `listmodels` calls. Explicit detach cleared the diagnostic. The malformed file included a dummy marker that never appeared in the replies.

The combined #861 helper also passed its original responsiveness regression. The local RPC completed before the paused upload was released. Upload integrity, retry, same-key replay, and budget/configuration persistence after restart passed.

- [Executed workflow](https://github.com/sunnyriverr/btx/blob/994f201578c4d42679d5400c898698a34ca40503/.github/workflows/session2-modelnet-saved-cloud-config-diagnostic-fix.yml) and [native status driver](https://github.com/sunnyriverr/btx/blob/994f201578c4d42679d5400c898698a34ca40503/proposal/observe.py)
- [Completed Linux run](https://github.com/sunnyriverr/btx/actions/runs/44463408299), [raw records](https://github.com/sunnyriverr/btx/actions/runs/44463408299/artifacts/14501038800), and [retained binaries](https://github.com/sunnyriverr/btx/actions/runs/44463408299/artifacts/14501118614)
- [Verified results, hashes and selected replies](result.json)

The executed target was standalone Linux x86-64 with OpenSSL 3.5.9 and a simulated loopback origin. The runner rebuilt the helper from retained `23ee567e` state with relevant ModelNet source matching release `a97af7b3`. It did not qualify the full node, a clean release build, real cloud authentication, other platforms or the full suite. A separate extracted-loader check on macOS used stubs and covered numeric conversion failure. The native fixture stays outside the default test runner.

Thanks to repch1c for the earlier cloud diagnostic in [#570](https://github.com/btxchain/btx/pull/570).
