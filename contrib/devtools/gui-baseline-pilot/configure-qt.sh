#!/bin/sh
# Preparation/configure only. Requires verified source and baseline-built static OpenSSL.
set -eu
: "${BTX_GUI_SOURCE:?exact ff5f source checkout required}"
: "${BTX_GUI_BUILD:?fresh isolated build directory required}"
: "${BTX_GUI_SSL:?baseline-built OpenSSL3.5.9 prefix required}"
test "$(git -C "$BTX_GUI_SOURCE" rev-parse HEAD)" = ff5f3f04ea11f044594987fc6be043ff68b136ad
test -z "$(git -C "$BTX_GUI_SOURCE" status --porcelain --untracked-files=no)"
test ! -e "$BTX_GUI_BUILD"
test -f "$BTX_GUI_SSL/lib/libssl.a"
test -f "$BTX_GUI_SSL/lib/libcrypto.a"
"$BTX_GUI_SSL/bin/openssl" version
cmake -S "$BTX_GUI_SOURCE" -B "$BTX_GUI_BUILD" -G Ninja \
 -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++ \
 -DBUILD_GUI=ON -DWITH_QT_VERSION=6 -DENABLE_WALLET=ON -DWITH_SQLITE=ON \
 -DWITH_MODELNET=ON -DWITH_ZMQ=ON -DWITH_BDB=OFF -DBUILD_TESTS=OFF \
 -DBUILD_GUI_TESTS=OFF -DBUILD_DAEMON=OFF -DBUILD_CLI=OFF -DBUILD_TX=OFF \
 -DBUILD_UTIL=OFF -DBUILD_WALLET_TOOL=OFF -DBUILD_BENCH=OFF -DWITH_CCACHE=OFF \
 -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DOPENSSL_USE_STATIC_LIBS=ON \
 -DOPENSSL_ROOT_DIR="$BTX_GUI_SSL" -DOPENSSL_INCLUDE_DIR="$BTX_GUI_SSL/include" \
 -DOPENSSL_SSL_LIBRARY="$BTX_GUI_SSL/lib/libssl.a" \
 -DOPENSSL_CRYPTO_LIBRARY="$BTX_GUI_SSL/lib/libcrypto.a"
ninja -C "$BTX_GUI_BUILD" -n btx-qt
# Build only after plan/profile checks: cmake --build "$BTX_GUI_BUILD" --target btx-qt --parallel 2
