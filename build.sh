#!/usr/bin/env bash
set -euo pipefail
export PATH="/opt/hostedtoolcache/Python/3.12.16/x64/bin:$PATH"
python3 - <<'PLAN'
import json
from pathlib import Path
r = json.loads(Path("pilot-records/result.json").read_text())
assert r["source"] == "88c9b49cb16360fc8fbf3f84003b8b54c29e6db5"
assert r["verdict"] == "PREPARATION_PASS" and r["product_compile_started"] is False
assert len(r["planned_step_lines"]) == 3547, "Ninja plan changed; review before compiling"
PLAN
build="$GITHUB_WORKSPACE/gui-pilot-runtime/qtbuild"
mapfile -t targets < <(python3 -c 'from build_targets import TARGETS; print(*TARGETS, sep="\n")')
test "${#targets[@]}" -eq 17
# Run the generated Qt icon rule first so missing renderer tools fail cheaply.
test -x /usr/bin/convert
timeout --kill-after=10s 90s cmake --build "$build" --parallel 2 --target generate_ico
timeout --kill-after=20s 68m cmake --build "$build" --parallel 2 --target "${targets[@]}"
curl -fsSL https://sh.rustup.rs -o /tmp/btx-rustup-init.sh
sh /tmp/btx-rustup-init.sh -y --profile minimal --default-toolchain none
export PATH="$HOME/.cargo/bin:$PATH"
rustup toolchain install 1.95.0 --profile minimal
rustc +1.95.0 --version
(
  cd product/gui/atlas
  CARGO_BUILD_JOBS=2 CARGO_TARGET_DIR="$GITHUB_WORKSPACE/atlas-target" timeout --kill-after=20s 35m cargo +1.95.0 build --locked --release -p btx-atlas
)
install -m 755 atlas-target/release/btx-atlas "$build/bin/btx-atlas"
test -z "$(git -C product status --porcelain --untracked-files=no)"
test -x "$build/bin/btx-guardd"
mkdir candidate-input
archive=candidate-input/btx-linux-gui-candidate.tar.gz
env -u BTX_RELEASE_GLIBC_CEILING python3 product/scripts/release/package_release_archive.py \
  --source-root product --output-dir candidate-input --version 0.34.16 --platform-id linux-x86_64 \
  --btxd "$build/bin/btxd" --btx-cli "$build/bin/btx-cli" --btx-util "$build/bin/btx-util" \
  --archive-name "${archive##*/}" --require-gui --require-model-helpers
env -u BTX_RELEASE_GLIBC_CEILING python3 product/scripts/release/verify_release_btxd.py --no-launch --archive "$archive" --require-model-helpers
python3 manifest.py
