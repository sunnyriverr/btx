#!/bin/sh
set -eu
cd "$(dirname "$0")"
cache=/tmp/btx-helper-full-20261102
build="$cache/build"
for variant in old new; do
    src="$PWD/$variant"
    sha256sum "$src/node/autoupdate.cpp" "$src/node/autoupdate.h"
    g++ -std=c++20 -O1 -ffunction-sections -fdata-sections -I"$src" -I"$build/src" -I"$cache/src" \
        -I"$cache/src/univalue/include" poller454.cpp "$src/node/autoupdate.cpp" -Wl,--gc-sections \
        -Wl,--start-group "$build/lib/libbitcoin_clientversion.a" "$build/lib/libbitcoin_util.a" \
        "$build/lib/libbitcoin_crypto.a" "$build/lib/libbitcoin_common.a" "$build/src/univalue/libunivalue.a" \
        -Wl,--end-group -levent -lssl -lcrypto -o poller454
    code=0
    ./poller454 "$PWD/poller-$variant" || code=$?
    printf '%s exit=%s\n' "$variant" "$code"
    rm poller454
    if [ "$variant" = old ]; then test "$code" = 42; else test "$code" = 0; fi
done
