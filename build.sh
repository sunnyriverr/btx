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
# Match the interpreter and absolute CMake path of the verified checkpoint.
python_setup=$(mktemp -d)
curl -fsSL --retry 2 --max-time 150 \
  https://github.com/actions/python-versions/releases/download/3.12.16-40260402378/python-3.12.16-linux-22.04-x64.tar.gz \
  -o "$python_setup/ubuntu-python.tar.gz"
echo "ebdd874c6bb02d1ade9069da60b6b09f8346ba0ae0db11e60e6ce90cf5542fb7  $python_setup/ubuntu-python.tar.gz" | sha256sum --check
mkdir "$python_setup/unpacked"
tar -xzf "$python_setup/ubuntu-python.tar.gz" -C "$python_setup/unpacked"
(cd "$python_setup/unpacked" && RUNNER_TOOL_CACHE=/opt/hostedtoolcache bash setup.sh)
builder_python=/opt/hostedtoolcache/Python/3.12.16/x64/bin/python3
"$builder_python" -VV
"$builder_python" -m pip install --disable-pip-version-check --no-deps cmake==3.31.6 ninja==1.12.1.1
tool_bin=${builder_python%/*}
ln -s "$tool_bin/cmake" /usr/local/bin/cmake
ln -s "$tool_bin/ninja" /usr/local/bin/ninja
/usr/local/bin/cmake --version
/usr/local/bin/ninja --version
"$builder_python" pilot.py
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
