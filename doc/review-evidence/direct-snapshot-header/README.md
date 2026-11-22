# Direct snapshot URL header wait

Tested the stock and patched wrappers on macOS with Python 3.9 using the published 228000 snapshot. Node CLI replies and time were simulated. The base was `release-0.34.17` at `7d65025bb3bff27e4f6c2fdc95f33e4b859a2df5`.

| Case | Stock | Patched |
| --- | --- | --- |
| Direct URL, base header arrives at 3 s | Load at 0 s, missing-base error | Waits and loads once at 3 s |
| Manifest, base header arrives at 3 s | Loads once at 3 s | Loads once at 3 s |
| Direct URL, base header already known | Loads once at 0 s | Loads once at 0 s |

Missing-header and stalled-CLI controls stopped at the 10-second fixture limit. A bad checksum stopped before polling and truncated metadata stopped before loading. All 18 existing wrapper tests passed on both versions. Live-node snapshot activation and mainnet sync were outside the test scope.

The [stock trace](paired-stock.json) and [candidate trace](paired-candidate.json) show ordered calls and verdicts, with scratch paths redacted. The [executed fixture](qualify.py) imports the pinned upstream test loader from `source/test/util/btx_faststart_test.py`. Put the stock wrapper under `source/contrib/faststart/`, the patched wrapper at `candidate/btx-faststart.py`, and the [published snapshot](https://github.com/btxchain/btx/releases/tag/assumeutxo-228000) beside the fixture as `snapshot.dat`. Run `python3 qualify.py stock` and `python3 qualify.py candidate`.
