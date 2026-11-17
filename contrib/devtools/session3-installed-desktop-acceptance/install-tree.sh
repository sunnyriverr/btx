#!/usr/bin/env bash
# Reuses Session2's prebuilt-tree boundary; no updater main(), download or build.
set -euo pipefail
umask 077
fixture=$1
unpacked=$2
prefix=$3
private=$4
mkdir -p "$private/home" "$private/cache" "$private/updater" "$private/links"
export HOME="$private/home" BTX_INSTALL_ROOT="$private/updater"
export BTX_LINK_DIR="$private/links" BTX_CACHE_ROOT="$private/cache"
export XDG_DATA_HOME="$private/home/data" XDG_CONFIG_HOME="$private/home/config"
export XDG_CACHE_HOME="$private/home/cache"
# Sourcing only defines functions; the upstream BASH_SOURCE guard excludes main.
source "$fixture/source/install.sh"
install_prebuilt_release_tree "$unpacked/bin" 0.34.16 "$prefix" linux-x86_64 \
  https://github.com/sunnyriverr/btx/actions/runs/44063898937/artifacts/14319148652 \
  074dac167c26c1e091198f691ed5727817dba88a
