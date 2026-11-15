#!/usr/bin/env bash
set -euo pipefail
mkdir -p records minio-image
trap 'status=$?; printf "%s\n" "$status" > records/wrapper-exit.txt' EXIT
# Exact same upstream MinIO executable/hash as the previously executed fixture.
tag=RELEASE.2025-04-22T22-12-26Z
curl -fsSL --max-time 120 --retry 2 "https://github.com/minio/minio/releases/download/$tag/minio.linux-amd64.$tag" -o minio-image/minio
(cd minio-image && echo '53e2a2cb16c5366ea6fbbc479c19ddb4c6a0948273e752f740fb1fbf27bb817c  minio' | sha256sum -c -)
chmod +x minio-image/minio
printf 'FROM scratch\nCOPY minio /minio\nENV HOME=/root\nENTRYPOINT ["/minio"]\n' > minio-image/Dockerfile
docker build -t btx-cloud-upload:owned minio-image
export BTX_MINIO_IMAGE
BTX_MINIO_IMAGE=$(docker image inspect --format '{{.Id}}' btx-cloud-upload:owned)
printf '%s\n' "$BTX_MINIO_IMAGE" > records/minio-image-id.txt
export BTX_UPLOAD_RECEIPT="$PWD/records/bounded-upload.json"
export UPLOAD_TMPDIR="/tmp/btx-upload-${GITHUB_RUN_ID}"
set +e
timeout --signal=TERM --kill-after=15s 600s python3 product/test/functional/minio_upload.py --configfile="$PWD/obj/test/config.ini" --tmpdir="$UPLOAD_TMPDIR" --timeout-factor=1 > records/native.log 2>&1
status=$?
set -e
printf '%s\n' "$status" > records/framework-exit.txt
if test -f "$UPLOAD_TMPDIR/bounded-upload.json"; then
  cp "$UPLOAD_TMPDIR/bounded-upload.json" records/
fi
if test -f "$UPLOAD_TMPDIR/test_framework.log"; then
  cp "$UPLOAD_TMPDIR/test_framework.log" records/
fi
python3 validate_minio.py records/bounded-upload.json "$status"
exit "$status"
