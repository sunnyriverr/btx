#!/usr/bin/env bash
set -euo pipefail
# Build test_btx using the repository instructions, then pass its path here.
# Each case/repetition is a separate process, matching the recorded runs.
test_binary=${1:?Usage: run-focused.sh /absolute/path/to/test_btx}
for test_name in snapshot_eviction_cooldown_survives_budget_marker_pressure snapshot_eviction_present_marker_allows_fresh_download_and_progress snapshot_evicted_body_becomes_background_root; do
  for repetition in 1 2 3; do
    printf '%s run %s
' "$test_name" "$repetition"
    BTX_MATMUL_BACKEND=cpu BTX_MATMUL_V4_BACKEND=cpu "$test_binary" --run_test="peerman_tests/$test_name" --log_level=message --report_level=detailed
  done
done
