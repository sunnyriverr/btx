#!/bin/sh
set -eu
for binary in before after; do
    source=src/node/resource_governor.cpp
    if [ "$binary" = after ]; then
        source=candidate/resource_governor.cpp
    fi
    g++ -std=c++20 -O0 -ffunction-sections -fdata-sections -Wl,--gc-sections \
        -pthread -Isrc -Isrc/univalue/include "$source" src/univalue/lib/*.cpp \
        probe.cpp -o "$binary"
    sha256sum "$binary"
done
