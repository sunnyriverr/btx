#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
src="$PWD/focused-source/src"
case_dir="$PWD/focused-check"
build="$case_dir/build"
records="$case_dir/records"
cxx=(clang++ -std=c++20 -O1 -g0 -ffunction-sections -fdata-sections
     -DDISABLE_OPTIMIZED_SHA256 -I"$build" -I"$src" -I/opt/homebrew/include)
compile() {
    local file="$1" output="$2"
    if [ ! -f "$build/$output.o" ] || [ "$file" -nt "$build/$output.o" ]; then
        "${cxx[@]}" -c "$file" -o "$build/$output.o" >"$records/$output.log" 2>&1
    fi
}
compile "$src/matmul/matmul_v4_rc_stage3.cpp" stage3
compile "$src/matmul/matmul_v4_rc_stage3_composition.cpp" composition
compile "$src/crypto/sha256.cpp" sha256
compile "$src/support/cleanse.cpp" cleanse
compile "$case_dir/codec-fixture.cpp" codec-fixture
for version in stock candidate; do
    source_dir="$src"
    if [ "$version" = candidate ]; then
        source_dir="$case_dir/candidate-src/src"
    fi
    compile "$source_dir/matmul/matmul_v4_rc_stage3_bounded_semantic_codec.cpp" "$version-codec"
    "${cxx[@]}" -Wl,-dead_strip "$build/$version-codec.o" "$build/codec-fixture.o" "$build/stage3.o" \
       "$build/composition.o" "$build/sha256.o" "$build/cleanse.o" -o "$build/$version-codec" \
       >"$records/$version-link.log" 2>&1
done
"$build/stock-codec" "$records/stock-envelope.bin"
"$build/candidate-codec" "$records/candidate-envelope.bin" "$records/stock-envelope.bin"
"$build/stock-codec" "$records/stock-cross-decode.bin" "$records/candidate-envelope.bin"
cmp "$records/stock-envelope.bin" "$records/candidate-envelope.bin"
cmp "$records/stock-envelope.bin" "$records/stock-cross-decode.bin"
shasum -a 256 "$records/"*-envelope.bin "$records/stock-cross-decode.bin"
