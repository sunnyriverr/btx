# Windows Unicode datadir path evidence

Base `c2e71aafc48a41593277e335c8bc370e45599f01`, candidate `e8ab27814e9faa9535fabf047dff72406efdd9b8`. The two product files carry the native path from SwapNet startup through the shared runtime. The fixture takes the actual node-side path expression from each source revision and exercises the real shared runtime with a disposable catalog.

## Windows

Windows Server 2022 x64, native MSVC 19.44.35230, Windows SDK 10.0.26100.0, ANSI code page 1252. The stock Unicode case created the catalog in a garbled sibling. The candidate created it only under the configured path. Both ASCII cases passed. Each case reopened its catalog in a fresh process, with the expected record and identical file bytes.

[Windows before and after](https://github.com/sunnyriverr/btx/actions/runs/46090764536/artifacts/15240913564) · [Windows results](windows-result.json)

## macOS

Mac ARM64, Apple Clang 17. Both revisions passed the ASCII and Unicode paths, private broker directory permissions, local socket creation and catalog reopen. The Windows and Mac receipts pin the same candidate source hashes. [Mac results](macos-result.json)

## Scope

Bas reported the stock failure in a full daemon. These before-and-after results are component tests. Full candidate daemon startup and migration of an existing misplaced catalog were outside the run. The candidate leaves old catalog files in place and preserves the separate SwapNet journal and vault paths. [Bas’s stock report](https://github.com/btxchain/btx/pull/714#issuecomment-7229637772)

The retained [fixture](path-fixture.cpp) and [runner](check.py) are the executed harness, with the checkout layout in the [fork controller](https://github.com/sunnyriverr/btx/tree/96c5b83d085bcdbc2981683bc605744e22492fde).
