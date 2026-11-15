#!/usr/bin/env bash
# Prepared Ubuntu runner entry point; NOT dispatched or executed locally.
set -euo pipefail
: "${RUNNER_TEMP:?owned hosted runner required}"
: "${BTX_MINIO_IMAGE:?pinned real MinIO image digest required}"
: "${SOURCEFILES_TMPDIR:?short fresh owned scratch required}"
case "$SOURCEFILES_TMPDIR" in /tmp/btx-sf-*) ;; *) exit 2 ;; esac
test ! -e "$SOURCEFILES_TMPDIR"
mkdir -p records
sha256sum -c expected-binaries.sha256
chmod +x obj/bin/btxd obj/bin/btx-cli obj/bin/btx-modeld
export BTXMODELD="$PWD/obj/bin/btx-modeld"
for file in base_minio.py source_files_cases.py validate_source_files.py; do cp "$file" "product/test/functional/$file"; done
set +e
timeout --kill-after=20s 900s /usr/bin/python3 product/test/functional/source_files_cases.py --configfile="$PWD/obj/test/config.ini" --tmpdir="$SOURCEFILES_TMPDIR" --nocleanup > records/native.log 2>&1
status=$?
set -e
printf '%s\n' "$status" > records/native-exit.txt
if test -f "$SOURCEFILES_TMPDIR/source-files-results.json"; then cp "$SOURCEFILES_TMPDIR/source-files-results.json" records/; fi
/usr/bin/python3 validate_source_files.py records
