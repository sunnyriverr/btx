# Separate87-request observation

These are existing logs from the successful pinned-Metal1024-body run of unchanged
#34070e35da0, NOT the capacity-patched199-body experiment. Source binary SHA256 is
12cde7f0cc4449cbac586d936d3616b17d6a71460ee5bfe7bb407bfa4315b4b7.
Source log SHA256 and exact extraction window are in retry/340-log-extraction.json.
Height964 hashbb921f0701f2292d28f99eb9a9e854bd3f79db1651fc8d34323d673164f0b700:
87 requesting-block and87 received-block messages. The target-events file includes
all matching events. The window file includes all requested diagnostic categories
across peers, sorted by wall timestamp with source-line tie breaks; source line
numbers are retained. No log message is fabricated. Category absence is limited
to that window. General received messages must not be attributed without the hash.

This proves request/body traffic in this run, not its cause. No store-full line
or requested timeout/reclaim/stale/idle message is present in the measured window.
Do not infer that the17th-body store failure caused this separate retry pattern.
The original run's mock clock advanced at real elapsed time, and unlimited regtest
pending/rate budgets differ from mainnet cap1. No rerun made for publication.
