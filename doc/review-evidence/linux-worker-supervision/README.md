# Linux filesystem-jail isolation: test evidence

Code/test branch: `codex/session2-linux-worker-supervision` at `896b57b325580dbfe49e2846e7ed3ba0e3f3ac08`, based on `46caec762b0f130d497313d8ca9fa6894ac19ccd`. Two focused commits; code/test tree is identical to tested `a35841c2b6dd1546a9a49c2599b72795a53694df`. identity-mapping.json records the history-only packaging.

The jail now uses a PID namespace with an init supervising an ordinary worker. Missing/invalid supervisory reports are explicit refusals; genuine worker126 and the existing address-space cap remain preserved.

Native execution: Alpine3.22.4/aarch64/musl, Linux6.12.81, GCC14.2, OpenSSL3.5.9. Fresh root CMake Release with BUILD_TESTS=ON and WITH_MODELNET=ON; wallet/GUI/daemon/CLI/utilities/SQLite/ZMQ/USDT/ccache off for this scoped profile. Guest libevent-dev setup is recorded.

Built both project-generated targets: test_swarm_fsjail_linux and src/modelnet/CMakeFiles/bitcoin_modelnet.dir/swarm_fsjail.cpp.o. The comparison used identical in-tree test/worker/CMake inputs. Before is the earlier PID candidate with the current cap, changing only the reporting delta—not a stock46 PID-isolation reproduction. Four report-fault assertions fail before and pass after; eight legitimate/refusal controls pass both. Corrected12/12. A lower inherited1GiB hard-cap control also passes12/12. Worker PID2, own-child fork/wait17 and actual inherited address limits are observed.

CTest ran with BTX_TEST_REQUIRE_LINUX_JAIL=1, so unavailable namespaces cannot count as a pass. Logs and comparison.json preserve each assertion and CTest return values. The first compile pilot corrected a missing copy_options argument before either final runtime comparison. All14,004 tracked regular source files matched the final local committed tree, zero mismatches. Internal review is not independent platform replication.

Limits: production object and dedicated regression, not the complete bitcoin_modelnet archive, test_btx/full suite, default daemon profile, actual model/package workload, glibc/other architectures, Windows/macOS runtime or release qualification. Fault injection is deliberate supervisor-channel testing, not evidence of natural frequency. Numeric EIO is source-verified; public refusal is observed. The separate SwarmRunConfined path is unchanged.

Original finding: repch1c ([338](https://github.com/btxchain/btx/issues/338)). Existing fail-closed pivot-root foundation: JPP ([346](https://github.com/btxchain/btx/pull/346)); its existing accepted authorship is retained in the base history. PID candidate/correction and these native checks: Sunny River. Numair requested the separate Linux follow-up on [338](https://github.com/btxchain/btx/issues/338#issuecomment-6620133855).

## Commands used

From a clean Linux checkout of the code/test branch, with project dependencies and static libc available:

```sh
cmake -S . -B build-fsjail -G Ninja -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=ON -DWITH_MODELNET=ON -DENABLE_WALLET=OFF -DWITH_SQLITE=OFF -DWITH_ZMQ=OFF -DBUILD_DAEMON=OFF -DBUILD_CLI=OFF -DBUILD_GUI=OFF -DBUILD_TX=OFF -DBUILD_UTIL=OFF -DBUILD_WALLET_TOOL=OFF -DWITH_USDT=OFF -DWITH_CCACHE=OFF
cmake --build build-fsjail --target test_swarm_fsjail_linux src/modelnet/CMakeFiles/bitcoin_modelnet.dir/swarm_fsjail.cpp.o -- -j1
BTX_TEST_REQUIRE_LINUX_JAIL=1 ctest --test-dir build-fsjail -R '^swarm_fsjail_linux_supervision$' -V --output-on-failure
```

To inspect the before control, use a separate disposable checkout, replace only src/modelnet/swarm_fsjail.cpp with before-reporting.cpp, and use the same build/test commands. Expected: scenarios4–7 fail and the other eight pass. Restore the code-branch TU and rebuild for12/12. The test target itself is unchanged. Routine non-required-jail execution returns explicit skip77 when the runtime jail is unavailable; target creation requires static libc, following the existing Linux probe guard.
