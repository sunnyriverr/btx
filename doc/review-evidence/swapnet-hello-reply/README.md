# Asymmetric SwapNet hello recovery

Follow-up to cb823a94f55685c60fd30e0b6d14d02ea1b951a8 (#630).
Credit to repch1c for the startup admission report and Numair for the periodic
hello retry introduced in d2334bcc.

The healthy paired transport admits both endpoints. If one initial hello is
missed while a runtime starts, one endpoint admits the peer and stops retrying.
The other endpoint retries, but the admitted endpoint rejects those hellos
without responding. The original code remained at admission1/0 after six
five-second retry rounds. The candidate queues one hello reply before first
admission. A full outbound queue defers admission until a reply can be queued.
Duplicate hellos remain rejected and do not generate responses.

The exact production Transport C++ component and maintained test were compiled
on macOS arm64 with Apple clang17.0.0, C++17, warnings as errors, pthreads and
assertions enabled. The same final test fails on baseline and passes on the
candidate. Both versions were built successfully. The unchanged original
standalone test passes on both versions.

Paired controls cover healthy delivery; left, right and both original hellos
missed; no retry before five seconds; transport provider frames in both
directions; duplicates; wrong network/unknown peers; full-queue deferral and
retry. Existing disable, disconnect, frame bounds, tokens, queues and concurrent
Send/GetStats checks are retained. Removing only the reply queue guard makes
the queue-pressure test fail. UBSan passes. ASan stalled in its own initializer
before main and supplied no test result.

## Reproduce

At the candidate commit, execute from the repository root:

```sh
clang++ -std=c++17 -Wall -Wextra -Werror -pthread -I src \
  src/swapnet/transport.cpp src/swapnet/test_transport.cpp -o /tmp/swapnet-transport
/tmp/swapnet-transport
```

For the paired baseline, retain the same final test_transport.cpp and compile
transport.cpp from cb823a94 instead. The baseline aborts on the missing endpoint's
admission assertion; the candidate prints that all transport assertions passed.
Use the [receipt](receipt.json) for the exact source, test and binary hashes,
and the [paired results](paired-results.json) for exit codes. The archived
[initial probe](admission-baseline.log) records healthy1/1 and missed-hello1/0.

The real native caller was traced: ProcessMessage and SendMessages register
connected peers through PeerReady, Receive drops frames while Current() is
absent, and Drain sends queued hello frames before SwapNet admission. This
establishes the startup route for the component failure. A complete daemon,
signed provider-catalog ingestion, financial workflow, Windows and Linux were
not executed here. Provider payloads are transport frame controls.
