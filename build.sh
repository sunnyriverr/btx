#!/usr/bin/env bash
set -euo pipefail
mkdir -p records
exec > >(tee records/build.log) 2>&1
. /etc/os-release
test "$VERSION_ID" = 24.04
test "$(uname -m)" = x86_64
source_commit=$(git -C product rev-parse HEAD)
test "$source_commit" = 88aeaac965f6ad0031aa6d8a062bfae23a45c4e0
test -z "$(git -C product status --porcelain)"
git -C product apply --check "$PWD/watch-wallet.patch"
git -C product apply "$PWD/watch-wallet.patch"
git -C product diff --check
git -C product diff --stat | tee records/source-diff.txt
sha256sum watch-wallet.patch | tee records/patch-sha256.txt
df -h .
free -m
sudo apt-get -o Acquire::Retries=1 update
sudo apt-get install -y --no-install-recommends libboost-dev libevent-dev libsqlite3-dev libzmq3-dev python3-dev python3-venv ninja-build
/usr/bin/python3 -m venv "$RUNNER_TEMP/swapnet-deps"
py="$RUNNER_TEMP/swapnet-deps/bin/python"
mkdir -p "$RUNNER_TEMP/swapnet-python-runtime"
"$py" -m pip install --disable-pip-version-check --only-binary=:all: --target "$RUNNER_TEMP/swapnet-python-runtime" cryptography==46.0.4
runtime_path=$(/usr/bin/python3 -I -c 'import sys; print(next(p for p in sys.path if p.startswith("/usr/local/") and p.endswith("/dist-packages")))')
sudo mkdir -p "$runtime_path"
sudo cp -a "$RUNNER_TEMP/swapnet-python-runtime/." "$runtime_path/"
/usr/bin/python3 -I -c 'import sys,sysconfig,sqlite3,cryptography; from cryptography.hazmat.primitives.ciphers.aead import AESGCM; assert cryptography.__version__=="46.0.4"; print(sys.version,sysconfig.get_config_var("SOABI"),sqlite3.sqlite_version,cryptography.__version__,cryptography.__file__)' | tee records/python.log
cmake -S product -B obj -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_DAEMON=ON -DBUILD_CLI=ON -DENABLE_WALLET=ON -DWITH_SQLITE=ON \
  -DBUILD_GUI=OFF -DWITH_MODELNET=OFF -DBUILD_TESTS=OFF -DPython3_EXECUTABLE=/usr/bin/python3 | tee records/configure.log
grep -E '^(ENABLE_WALLET|WITH_SQLITE|WITH_MODELNET|BUILD_DAEMON|BUILD_CLI|_Python3_(EXECUTABLE|LIBRARY_RELEASE|INCLUDE_DIR)):' obj/CMakeCache.txt | tee records/selected-config.txt
grep -Fx ENABLE_WALLET:BOOL=ON records/selected-config.txt
grep -Fx WITH_SQLITE:BOOL=ON records/selected-config.txt
jobs=$(nproc)
if (( jobs > 4 )); then jobs=4; fi
timeout --kill-after=25s 43m ninja -C obj -j "$jobs" btxd btx-cli
mkdir -p payload/bin payload/python
install -m 755 obj/bin/{btxd,btx-cli} payload/bin/
cp -a "$RUNNER_TEMP/swapnet-python-runtime/." payload/python/
find payload/python -type d -name __pycache__ -prune -exec rm -rf {} +
cp records/{python.log,selected-config.txt,patch-sha256.txt} payload/
printf '%s\n' "$source_commit" > payload/source.txt
for bin in btxd btx-cli; do
  ldd "payload/bin/$bin" | tee "records/$bin-ldd.log"
  ! grep -q 'not found' "records/$bin-ldd.log"
done
grep -q 'libpython3.12.so' records/btxd-ldd.log
(cd payload && find bin python -type f -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS && sha256sum -c SHA256SUMS >/dev/null)
head -2 payload/SHA256SUMS
echo BTX_WALLET_BINARIES_READY
