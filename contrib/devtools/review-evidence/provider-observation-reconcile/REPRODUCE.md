# Focused reproduction

Build btx-modeld atcbf65894plus the previously reviewed eaffe632helper change, and atcbf65894plus combined.patch. Do not stack both whole patches; the revision replaces the earlier per-action cleanup. The measured local build.py compiles each full helper translation unit and links identical cached CMake archives privately. Build/source/binary/link archive identities are retained. It is a local cached-build recipe, not a portable clean-build claim.

Place binaries at baseline/btx-modeld and candidate/btx-modeld next to reproduce.py and rpc_util.py. Run:

    python3 reproduce.py baseline
    python3 reproduce.py candidate

The final script records its verdict in baseline-result.json/candidate-result.json after executing all controls; a completed script exit alone is insufficient. Require baseline's5safety-related failures and22passing controls; require corrected27/27. Each test starts/stops only its own helper in a fresh temporary directory, with synthetic SafeTensors and no public peers, and removes the directory. No node, wallet or GPU is used.

projection-test.cpp compiles an exact extracted projection body with narrow ID/catalog/observation adapters. It checks remote partial metadata preservation, seeded completeness, transitions/removal and no mutation of the cached remote map. It does not execute actual catalog MarkIncomplete or peer transfer:

    c++ -std=c++20 -Wall -Wextra -Werror projection-test.cpp -o projection-test
    ./projection-test

See REPORT.md for source-level coverage of the remaining unseed routes, lock/platform review, timestamp semantics and limits. Report one final run per native variant; don't turn distinct cases into repetition counts.
