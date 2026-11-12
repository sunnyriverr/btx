#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
old=../hydration-resume/source/src
config=../hydration-resume/config
repo=../../../../btx-modelnet-integration
revision=1ccb08cf036ad029565e11c1884a231f0f0b444e
sources=(random.cpp randomenv.cpp logging.cpp sync.cpp crypto/{sha256,chacha20,siphash}.cpp support/{cleanse,lockedpool}.cpp util/{time,syserror,threadnames}.cpp)
for path in "${sources[@]}"; do
  mkdir -p "$(dirname "source/src/$path")"
  git -C "$repo" show "$revision:src/$path" > "source/src/$path"
done
extra=("${sources[@]/#/source/src/}")
common=(c++ -std=c++20 -O1 -I"$config" -Isource/src -I"$old" -I"$old/univalue/include" -I/opt/homebrew/opt/boost@1.85/include -Wl,-dead_strip)
shared=("$old"/crypto/{sha384,sha512,hex_base}.cpp "$old"/util/{fs,fs_helpers,check}.cpp)
modes=(baseline candidate)
if [[ $# -gt 0 ]]; then modes=("$@"); fi
for mode in "${modes[@]}"; do
  if [[ $mode == baseline ]]; then
    stream="$old/modelnet/file_stream.cpp"
    realm=../lab-bundle/source/src/modelnet/realm_channel.cpp
    writer="$old/util/readwritefile.cpp"
  else
    stream=source/src/modelnet/file_stream.cpp
    realm=source/src/modelnet/realm_channel.cpp
    writer=source/src/util/readwritefile.cpp
  fi
  "${common[@]}" hydration.cpp "$stream" "$writer" "${shared[@]}" "$old"/modelnet/{store,qualification,types,crypto}.cpp "$old"/util/strencodings.cpp "$old"/univalue/lib/*.cpp "${extra[@]}" -o "hydration-$mode"
  "${common[@]}" bundle.cpp "$realm" "$writer" "${shared[@]}" "${extra[@]}" -o "bundle-$mode"
done
