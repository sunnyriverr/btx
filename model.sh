#!/usr/bin/env bash
set -euo pipefail
archive=candidate-input/btx-linux-gui-candidate.tar.gz
export BTX_CANDIDATE_SHA256
BTX_CANDIDATE_SHA256=$(jq -er .candidate_archive_sha256 candidate-input/provenance.json)
echo "$BTX_CANDIDATE_SHA256  $archive" | sha256sum --check
mkdir package model-results
tar -xzf "$archive" -C package
engine/bin/pip freeze > model-results/engine-versions.txt
export BTX_TEST_PUBLISHER=10.252.10.17
sudo ip addr add "$BTX_TEST_PUBLISHER/32" dev lo
trap 'sudo ip addr del "$BTX_TEST_PUBLISHER/32" dev lo' EXIT
chmod +x generate_local.py
export PATH="$PWD/engine/bin:$PATH" BTX_MODEL_GENERATE="$PWD/generate_local.py"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=1
status=0
for mode in discovery interruption; do
    mkdir evidence
    if [ "$mode" = interruption ]; then
        export BTX_TEST_INTERRUPTION=1
    fi
    timeout --kill-after=10s 180s engine/bin/python -u native_fixture.py || status=1
    mv evidence "model-results/$mode"
done
exit "$status"
