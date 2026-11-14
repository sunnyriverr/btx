#!/usr/bin/env bash
set -euo pipefail
mkdir -p records
exec > >(tee records/run.log) 2>&1
head=8d6d8b1aabf371b12f2b1f5797b950fed7962d4e
test "$(git -C product rev-parse HEAD)" = "$head"
git -C product rev-parse HEAD
docker version --format '{{.Server.Version}}'
image=minio/minio:RELEASE.2025-04-22T22-12-26Z
timeout 180 docker pull "$image"
export BTX_MINIO_IMAGE
BTX_MINIO_IMAGE=$(docker image inspect --format '{{.Id}}' "$image")
docker image inspect --format '{{json .RepoDigests}} {{.Id}}' "$image" | tee records/image.txt
sudo apt-get update -qq
sudo apt-get install -y -qq libboost-dev libevent-dev libsqlite3-dev libzmq3-dev python3-dev python3-cryptography ninja-build
/usr/bin/python3 -I -c 'import cryptography,sqlite3; print(cryptography.__version__,sqlite3.sqlite_version)'
openssl_commit=636dfadc70ce26f2473870570bfd9ec352806b1d
curl -fsSL --retry 2 "https://codeload.github.com/openssl/openssl/tar.gz/$openssl_commit" | tar -xz
(
  cd "openssl-$openssl_commit"
  ./Configure --prefix="$PWD/../ssl" --libdir=lib no-shared no-tests
  make -j "$(nproc)"
  make install_sw
) > records/openssl.log 2>&1
cmake -S product -B obj -G Ninja -DCMAKE_BUILD_TYPE=Release  -DENABLE_WALLET=ON -DWITH_SQLITE=ON -DBUILD_TESTS=OFF -DBUILD_GUI=OFF  -DWITH_MODELNET=ON -DPython3_EXECUTABLE=/usr/bin/python3  -DOPENSSL_ROOT_DIR="$PWD/ssl" -DOPENSSL_USE_STATIC_LIBS=ON | tee records/configure.log
grep -Fx WITH_MODELNET:BOOL=ON obj/CMakeCache.txt
jobs=$(nproc)
if (( jobs > 4 )); then jobs=4; fi
cmake --build obj -j "$jobs" --target btxd btx-cli btx-modeld > records/build.log 2>&1
sha256sum obj/bin/{btxd,btx-cli,btx-modeld} | tee records/binaries.sha256
cp test.py product/test/functional/strict_minio_recovery.py
export BTXMODELD="$PWD/obj/bin/btx-modeld"
timeout 12m /usr/bin/python3 product/test/functional/strict_minio_recovery.py  --configfile="$PWD/obj/test/config.ini" --tmpdir="$RUNNER_TEMP/btx-minio-regtest" --nocleanup | tee records/test.log
grep -F MINIO_RECOVERY_BYTE_IDENTICAL records/test.log
grep -F 'modelnet MinIO layout e2e passed' records/test.log
