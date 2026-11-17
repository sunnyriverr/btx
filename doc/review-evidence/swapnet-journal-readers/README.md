# Complete journal readers — Mac component qualification

**Fix: retained closed history must not hide eligible sessions from scheduling, active-asset safety checks or owned audit events.** Tested production base `371013d61dc124a363521df5b94e97f64d2464f2`; candidate `ee84e2b6d15698a137aec6f4a9291d29671bdf49`.

The fix uses bounded stage-filtered keyset rotation (four active sessions plus one due terminal watch), an exhaustive active-asset scan with bounded memory, and ownership lookup for IDs referenced by the current bounded audit page. It preserves public listing limits, durable history, terminal cadence and raw event cursor semantics. No schema migration, consensus/chain rules or financial execution policy changed.

## Executed results

Mac ARM64, Python 3.12.14, pytest 8.4.2. Actual Store/Journal/Application/Coordinator code and SQLite transactions. Sessions/agreements, tick callbacks, driver factories, chains and signing in the component fixtures are synthetic or simulated. No native daemon, actual funded swap, Linux/Windows execution or full-suite/release qualification claimed.

| Same maintained regression inventory | Stock | Candidate |
| --- | --- | --- |
| First 12 cases | 5 fail / 7 pass | 12 pass |
| Two additional review-driven over-cap/stage-change cases | 1 fail / 1 pass | 2 pass |
| Total across disjoint runs | **6 fail / 8 pass** | **14 pass** |

All three original contracts fail stock and pass candidate. Controls include reopen, retained history, seven-active/four-per-pass fairness, complete/refunded cadence and wrap, 4,097 terminal rows plus active work, 130 reopened active sessions, guard refusal before driver side effects, unrelated-asset permission, owner visibility, 500 event IDs, exact `swap_id`/`id` precedence, cross-principal isolation and continuation. Assertions exercise behavior rather than private helper names.

**108 existing compatibility cases passed:** execution, runtime recovery, funding scans/capacity, atomic closeout, journal polling, terminal observation persistence, timestamp capacity, maker terminal capacity and offline terminal cleanup.

Existing controls initially yielded 81 passes and 27 stops at their free-disk assertion before their test bodies. Only those 27 were rerun after restoring the space reserve; all passed. Initial collection with the system Python 3.9 failed on unsupported union annotations; qualification used the existing Python 3.12 runtime. Logs preserve both setup failures separately from product results. Closed disposable test data and the prior wallet-disabled zero-block runtime were losslessly archived and hash-verified; no wallets, binaries, compiled caches or active peer data removed. No valid passes repeated merely to obtain a clean aggregate badge.

## Reproduction in a checkout

With Python 3.12, pytest and the existing SwapNet test dependencies:

```sh
PYTHONPATH=contrib/swapnet python3.12 -m pytest contrib/swapnet/tests/test_journal_reader_completeness.py -q
```

For the stock comparison, put the identical new test file on base371013d6. These are portable checkout commands; actual local runs used a launcher selecting isolated baseline/candidate roots and the already-installed Python packages. New cases were run as the first12 followed by the two added cases selected with `-k 'legacy_overcap or active_terminal_stage_changes'`; logs below are authoritative for execution, not an assertion of one fresh whole-repository run.

`qualification.json` identifies exact tested production/test hashes. Logs are path-sanitized only; `MANIFEST.json` hashes the published bytes. `REPAIR-REVIEW.md` is an internal independent source review, not independent platform execution. Original source/test evidence is retained locally.

Credit: builds on Numair’s SwapNet journal and the existing capacity fixture in `test_funding_scan_and_capacity.py`; its helper is explicitly attributed in the maintained regression. Prior recovery, principal and native coverage from repch1c and Jpp-matata was reused, not claimed as our new work. This patch and qualification used AI assistance; the actual Mac results and limitations are listed above.

The pending #749 backoff change remains author-owned and separate. Its scheduling hunk may need a context refresh against this selector change; its retry policy is not reimplemented here.
