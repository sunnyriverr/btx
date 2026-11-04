# Current LAN receive-interface fix — evidence

Code: `3acc3f74d92f646cf95cdcb8c4d92a7ec97afc9a` on `codex/lan-scope-current46`, based on accepted `46caec762b0f130d497313d8ca9fa6894ac19ccd`. Original report: repch1c ([338](https://github.com/btxchain/btx/issues/338)); correction/current integration: Sunny River; earlier contributor review/guidance: JPP. Existing base authorship and the previously tested af1ffda2 candidate are retained.

The three-file integration preserves accepted ValidPort byte-for-byte, including IsForbiddenControlPort. The Windows shim differs only by the required early mswsock.h include; existing native CRT and FAR/NEAR changes remain. integration.json records these checks. No header/default-fetch policy change is included.

## Current checks

- Linux: existing Alpine3.22.4/aarch64/musl VM, kernel6.12.81, GCC14.2, OpenSSL3.5.9. Fresh root CMake Release/O1, testsON/ModelnetON, wallet/daemon/GUI/CLI/utilities/SQLite/ZMQ/USDT/ccache off. Actual native_discovery, model_nat, helper consumer and native_discovery_tests objects compile. This is not a full archive/helper/test_btx link or run.
- A separate component executable uses actual native_discovery.cpp and actual model_nat.cpp; function/data sections and linker GC discard unrelated NAT routines. No policy stubs/adapters. All22 protected ports remain refused and two ordinary codec/hint controls pass. Real Open/Tick retains an ordinary selected-interface TTL0 multicast hint; idle is nonblocking. Own-host unicast is also observed in output, but is routing-dependent and does not gate the process exit. Current checks observe hints, not peer connections.
- Mac: current complete discovery TU compiles natively with C++20/O1 and project-style warnings/unused-parameter handling. Direct compiler check, not a current root/helper runtime result. Initial overly strict common-header flags and correction are retained as a pilot, with no source change.
- Windows: Mac Clang x86_64 Windows target against genuine pinned MinGW headers (70d3f1ac8cffdb8ac48f4190da67aa295dddc8fd). Current shim prelude plus required receive declarations fails with a late first mswsock include and passes with the combined early include. This tests the candidate include-order prerequisite, not a stock46 native-Windows failure. One existing MinGW SDK warning remains.

All14,002 tracked regular files matched the final guest sources, zero mismatches. Source and object/binary hashes are supplied. Maintained native_discovery_tests compiled only; it does not exercise the receiver. controls.cpp is the separate positive receiver/policy fixture. Internal review is not independent human/platform replication.

## Remaining native Windows qualification

Build/link the actual discovery/helper component using native MSVC/clang-cl CMake/shim/SDK settings, then exercise Open/join/nonblocking receive with real interface and destination metadata, selected multicast and unicast and interface changes. No full Windows TU, link or runtime is claimed by the MinGW header fixture. Also unqualified: physical multi-host topology, external routing matrix, glibc/other architectures, full suite, default daemon profile, completed authentication/model transfer and release.

Historical Mac/Linux unwanted-dial and synthetic-policy evidence is retained at its original [public handoff](https://github.com/btxchain/btx/issues/338#issuecomment-6554059976) and af1ffda2 sources; it was not rerun or relabeled current. This integration fills current build/legitimate-receiver gaps only.

## Commands used

From a clean checkout of this code branch, with ordinary project dependencies:

```sh
cmake -S . -B build-lan -G Ninja -DCMAKE_BUILD_TYPE=Release '-DCMAKE_CXX_FLAGS_RELEASE=-O1 -DNDEBUG' -DBUILD_TESTS=ON -DWITH_MODELNET=ON -DBUILD_DAEMON=OFF -DBUILD_CLI=OFF -DBUILD_GUI=OFF -DBUILD_TX=OFF -DBUILD_UTIL=OFF -DBUILD_WALLET_TOOL=OFF -DENABLE_WALLET=OFF -DWITH_SQLITE=OFF -DWITH_ZMQ=OFF -DWITH_USDT=OFF -DWITH_CCACHE=OFF
cmake --build build-lan --verbose --target src/modelnet/CMakeFiles/bitcoin_modelnet.dir/native_discovery.cpp.o src/modelnet/CMakeFiles/bitcoin_modelnet.dir/model_nat.cpp.o src/modelnet/CMakeFiles/bitcoin_modelnet.dir/helper.cpp.o src/test/CMakeFiles/test_btx.dir/native_discovery_tests.cpp.o -- -j1
g++ -std=c++20 -O1 -pthread -ffunction-sections -fdata-sections -Isrc -Ibuild-lan/src src/modelnet/native_discovery.cpp src/modelnet/model_nat.cpp /path/to/evidence/controls.cpp -Wl,--gc-sections -o build-lan/lan-controls
# Use the private IPv4 of the selected local test interface; observed host:192.168.5.15.
build-lan/lan-controls PRIVATE_TEST_IPV4
```

Run socket controls in a disposable test environment with discovery UDP29448 free. The fixture's multicast TTL is zero and it does not start a helper or make model-peer connections. Protected-port/ordinary-codec/multicast checks determine exit status; own-host unicast is an additional recorded observation. No full helper or default test-runner coverage follows from that component executable.

The VM was stopped, its temporary2GiB memory restored to1GiB, and no owned test/helper remained. No production/wallet or peer-session work changed. Local workspace prefixes are redacted in public fixture/log copies; path-redactions.json maps original/public hashes. Raw local qualification records remain preserved.
