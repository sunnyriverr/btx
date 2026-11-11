#!/usr/bin/env bash
set -euo pipefail
. /etc/os-release
test "$VERSION_ID" = 22.04
test "$(uname -m)" = x86_64
export DEBIAN_FRONTEND=noninteractive
apt-get -o Acquire::Retries=2 update
apt-get install -y --no-install-recommends ca-certificates curl git build-essential cmake ninja-build pkg-config python3 perl libboost-dev libevent-dev libsqlite3-dev libzmq3-dev libqrencode-dev qt6-base-dev qt6-base-dev-tools qt6-tools-dev qt6-tools-dev-tools qt6-l10n-tools libwebkit2gtk-4.1-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev librsvg2-bin libxdo-dev patchelf
git config --global --add safe.directory "$GITHUB_WORKSPACE/accepted-source"
git config --global --add safe.directory "$GITHUB_WORKSPACE/product"
getconf GNU_LIBC_VERSION
python3 pilot.py
build="$GITHUB_WORKSPACE/gui-pilot-runtime/qtbuild"
mapfile -t targets < <(python3 -c 'from build_targets import TARGETS; print(*TARGETS, sep="\n")')
test "${#targets[@]}" -eq 17
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
