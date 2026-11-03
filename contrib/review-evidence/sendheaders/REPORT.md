# BTX sendheaders regression coverage

The test-only repair at `03934978ab6c186bd57d08f6adafb6f8aeb04f7d` completes all five sections of `p2p_sendheaders.py`. The identical final fixture passed twice on macOS. In both paired runs, omitting only the ordinary-path isolation reproduced the original exact INV assertion failure.

## Why the existing test failed

The baseline fixture expects INV before SENDHEADERS. BTX instead proactively sends HEADERS plus the full BLOCK to a modern peer whose parent is known; its sent-header cursor then suppresses redundant INV. This was observed in the original height-3 diagnostic. It establishes an outdated fixture expectation, not a demonstrated production relay failure. The baseline failure was also reported in PRs #314 and #375; #375 repairs a different chunk-transport test.

The repair first verifies fresh proactive delivery: the exact mined header and serialized full body must match RPC, with no SENDHEADERS, outbound GETDATA or INV. It then mines and invalidates a 512-block warmup branch. Keeping the PeerManager alive retains its fast-announcement high-water height of 514, allowing the original ordinary announcement cases to run below that height. Every later construction/mining path is height-bounded. No production relay switch or rule is changed.

## Later fixture prerequisites

Restoring the whole test exposed three further assumptions:

- The synthetic VERSION advertised an unknown starting height. The fixture now supplies its actual handshake height, retaining the NODE_WITNESS-only direct-fetch profile. Unknown-height negative profiles are not qualified here.
- Live fork construction sometimes delivered an equal-work reorg as eight headers followed by one, rather than a nine-header batch. A temporary peer now stages the complete headers; descendants are cached through reverse-order submitblock and the missing root is supplied last. The original active tip must remain unchanged until that root, then become the exact replacement tip. Original observers and their cursors remain intact. This tests node0's outgoing reorg-announcement selection, not live streamed fork propagation between the two real nodes.
- BTX rate-limits GETHEADERS by the last send for 120 seconds and disconnects after eleven unconnecting messages. Part5 now verifies 100 successful missing-parent recoveries outside that window, then ten tolerated announcements without another request and the exact eleventh-message flood disconnect inside a fixed window. Nodes synchronize before clock advances; pending bodies are drained first.

Parts1–4 retain their exact substantive INV/header/source/request/direct-fetch assertions. Part5 deliberately replaces the obsolete repeated-immediate-request expectation.

## Observed results and provenance

The final fixture completed in 67.37 and 66.31 seconds. Both paired controls failed precisely at the first ordinary INV assertion. The retained final node logs show both intended eight-header announcements, both long-reorg INV fallbacks, all 100 recoveries, terminal active height 406 and the exact eleven-message flood reason. See `summary.json`, `paired-run.json`, `identity.json` and the compressed logs. Public log copies replace the personal workspace/home prefixes with `<workspace>`/`<home>`; private originals remain hash-verified.

Native macOS arm64; two disposable wallet-disabled regtest nodes; Modelnet disabled; official generic-P2P MatMul preactivation flags; timeout factor 1. The reused binary is tree `45db5cca94751e59ac09b8f05e165ae24988a2f4`: base `cbf65894e6d61084527cd93e913a00c6794418dd` plus #377/#378 RPC/helper changes. Its `net_processing.cpp` matches base exactly. This is not a new pristine-base build, GPU/ExactReplay, full-suite, mainnet, restart, release or native Linux/Windows qualification.

## Failed pilots and collection limits

Private pilot evidence preserves the unknown-height request failure, stale Part5 timing expectation and actual eight-plus-one reorg race. The first complete pass had an outer collector error because successful framework cleanup had already removed the datadir. The unchanged fixture was repeated with `--nocleanup` to preserve full logs and check the formerly intermittent reorg setup. These are fixture/collection findings, not product regressions.

The final collector initially mislabeled its initial free-space value as a minimum. Metadata now separates the initial reading from the actual per-run minimum, without altering run observations. The measured minimum was 1,346,674,688 bytes, above the required 1,342,177,280-byte reserve.

The practical lesson is to restore the supported scenario contract and retain precise negative controls, rather than accepting arbitrary relay messages or relying on background scheduling to create a batch.
