#!/usr/bin/env bash
set -euo pipefail
mkdir -p records minio-image
trap 'status=$?; printf "%s\n" "$status" > records/wrapper-exit.txt' EXIT
tag=RELEASE.2025-04-22T22-12-26Z
curl -fsSL --max-time 120 --retry 2 "https://github.com/minio/minio/releases/download/$tag/minio.linux-amd64.$tag" -o minio-image/minio
(cd minio-image && echo '53e2a2cb16c5366ea6fbbc479c19ddb4c6a0948273e752f740fb1fbf27bb817c  minio' | sha256sum -c -)
chmod +x minio-image/minio
printf 'FROM scratch\nCOPY minio /minio\nENV HOME=/root\nENTRYPOINT ["/minio"]\n' > minio-image/Dockerfile
docker build -t btx-sourcefiles-preflight:owned minio-image
export BTX_MINIO_IMAGE SOURCEFILES_TMPDIR
BTX_MINIO_IMAGE=$(docker image inspect --format '{{.Id}}' btx-sourcefiles-preflight:owned)
SOURCEFILES_TMPDIR="/tmp/btx-sf-${GITHUB_RUN_ID}"
printf '%s\n' "$BTX_MINIO_IMAGE" > records/minio-image-id.txt
set +e
bash run-cases.sh
status=$?
set -e
if test -d "$SOURCEFILES_TMPDIR"; then
  python3 collect.py "$SOURCEFILES_TMPDIR"
fi
exit "$status"
