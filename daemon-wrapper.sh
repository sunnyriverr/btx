#!/bin/bash
args=()
for arg in "$@"; do
  case "$arg" in
    -modelnet=0|-modelbind=off|-nomodelnet) ;;
    *) args+=("$arg");;
  esac
done
exec /Volumes/BTXDeposit/build/bin/btxd "${args[@]}"
