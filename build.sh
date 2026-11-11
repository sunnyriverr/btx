#!/usr/bin/env bash
set -euo pipefail
. /etc/os-release
test "$VERSION_ID" = 22.04
test "$(uname -m)" = x86_64
export DEBIAN_FRONTEND=noninteractive
apt-get -o Acquire::Retries=2 update
apt-get install -y --no-install-recommends ca-certificates curl git build-essential cmake ninja-build pkg-config python3 perl libboost-dev libevent-dev libsqlite3-dev libzmq3-dev libqrencode-dev qt6-base-dev qt6-base-dev-tools qt6-tools-dev qt6-tools-dev-tools qt6-l10n-tools libwebkit2gtk-4.1-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev librsvg2-bin libxdo-dev patchelf imagemagick
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
"$builder_python" -m pip install --disable-pip-version-check --no-deps cmake==3.31.6 ninja==1.11.1.4
tool_bin=${builder_python%/*}
ln -s "$tool_bin/cmake" /usr/local/bin/cmake
ln -s "$tool_bin/ninja" /usr/local/bin/ninja
/usr/local/bin/cmake --version
/usr/local/bin/ninja --version
"$builder_python" -u qualify.py
