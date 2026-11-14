#!/usr/bin/env bash
set -euo pipefail
mkdir -p records payload/bin payload/python
exec > >(tee records/build.log) 2>&1
. /etc/os-release
test "$VERSION_ID" = 24.04
test "$(uname -m)" = x86_64
python3 - <<'PY'
import shutil,json,hashlib,pathlib,subprocess
assert shutil.disk_usage('.').free >= 8*1024**3, 'Need 8GiB free'
p=pathlib.Path('product');m=json.loads(pathlib.Path('candidate-manifest.json').read_text())
for f,h in m['files'].items():
 assert hashlib.sha256((p/f).read_bytes()).hexdigest()==h,f
print('ALL_CANDIDATE_HASHES_MATCH')
pathlib.Path('records/source.txt').write_text(subprocess.check_output(['git','-C','product','rev-parse','HEAD'],text=True))
PY
df -h .; free -m
sudo apt-get -o Acquire::Retries=1 update
sudo apt-get install -y --no-install-recommends libboost-dev libevent-dev libsqlite3-dev libzmq3-dev python3-dev python3-venv ninja-build ccache zstd
/usr/bin/python3 -m venv "$RUNNER_TEMP/swapnet-deps"
"$RUNNER_TEMP/swapnet-deps/bin/python" -m pip install --only-binary=:all: --target "$RUNNER_TEMP/swapnet-runtime" cryptography==46.0.4
runtime_path=$(/usr/bin/python3 -I -c 'import sys; print(next(p for p in sys.path if p.startswith("/usr/local/") and p.endswith("/dist-packages")))')
sudo mkdir -p "$runtime_path"
sudo cp -a "$RUNNER_TEMP/swapnet-runtime/." "$runtime_path/"
/usr/bin/python3 -I -c 'import sys,sysconfig,sqlite3,cryptography; from cryptography.hazmat.primitives.ciphers.aead import AESGCM; print(sys.version,sysconfig.get_config_var("SOABI"),sqlite3.sqlite_version,cryptography.__version__)' | tee records/python.log
c++ --version | head -1
ccache --show-stats | tee records/cache-before.txt
cmake -S product -B obj -G Ninja -DCMAKE_BUILD_TYPE=Release -DBUILD_DAEMON=ON -DBUILD_CLI=ON -DENABLE_WALLET=ON -DWITH_SQLITE=ON -DBUILD_GUI=OFF -DWITH_MODELNET=OFF -DBUILD_TESTS=OFF -DPython3_EXECUTABLE=/usr/bin/python3 -DCMAKE_C_COMPILER_LAUNCHER=ccache -DCMAKE_CXX_COMPILER_LAUNCHER=ccache | tee records/configure.log
cp obj/CMakeCache.txt records/
ninja -C obj -n btxd btx-cli > records/build-plan.txt
head -3 records/build-plan.txt; tail -3 records/build-plan.txt
python3 -c 'import shutil; assert shutil.disk_usage(".").free>=6*1024**3,"Need6GiB after configure"'
timeout --kill-after=25s 35m ninja -C obj -j 4 btxd btx-cli
install -m755 obj/bin/{btxd,btx-cli} payload/bin/
cp -a "$RUNNER_TEMP/swapnet-runtime/." payload/python/
for b in btxd btx-cli; do ldd "payload/bin/$b" | tee "records/$b-ldd.txt"; ! grep -q 'not found' "records/$b-ldd.txt"; done
find obj -path '*swapnet*' -name frozen_sources.h -exec sha256sum '{}' \; > records/frozen-hash.txt
test -s records/frozen-hash.txt
cp candidate-manifest.json payload/
cp records/source.txt payload/
(cd payload && find bin python -type f -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS && sha256sum -c SHA256SUMS >/dev/null)
echo COMBINED_NATIVE_BUILD_PASS
