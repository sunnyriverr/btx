#!/usr/bin/env bash
set -euo pipefail

mkdir -p evidence
exec > >(tee evidence/preflight.log) 2>&1
scratch=$(mktemp -d)
container=modelnet-minio-preflight
trap 'docker logs "$container" > evidence/minio.log 2>&1 || true; docker rm -f "$container" >/dev/null 2>&1 || true; rm -rf "$scratch"' EXIT
mkdir "$scratch/pkg" "$scratch/image" "$scratch/tls"
tag=RELEASE.2025-04-22T22-12-26Z
curl -fsSL --max-time 120 --retry 2 "https://github.com/minio/minio/releases/download/$tag/minio.linux-amd64.$tag" -o "$scratch/image/minio"
(cd "$scratch/image" && echo '53e2a2cb16c5366ea6fbbc479c19ddb4c6a0948273e752f740fb1fbf27bb817c  minio' | sha256sum -c -)
chmod +x "$scratch/image/minio"
printf 'FROM scratch\nCOPY minio /minio\nENV HOME=/root\nENTRYPOINT ["/minio"]\n' > "$scratch/image/Dockerfile"
docker build --quiet -t modelnet-minio-preflight "$scratch/image"
export BTX_MINIO_IMAGE=modelnet-minio-preflight
curl -fsSL --max-time 120 --retry 2 https://github.com/btxchain/btx/releases/download/v0.34.17/btx-0.34.17-x86_64-linux-gnu.tar.gz -o "$scratch/btx.tar.gz"
bash preflight-linux.sh "$scratch/btx.tar.gz" "$scratch/pkg"
cp "$scratch/pkg/modeld-loader.log" evidence/
openssl req -x509 -newkey rsa:2048 -nodes -days 1 -subj /CN=localhost \
  -addext 'subjectAltName=DNS:localhost' -keyout "$scratch/tls/private.key" \
  -out "$scratch/tls/public.crt" 2>"$scratch/openssl.log"
chmod 600 "$scratch/tls/private.key"
docker run -d --name "$container" -p 127.0.0.1::9000 \
  -v "$scratch/tls:/certs:ro" "$BTX_MINIO_IMAGE" server /data --certs-dir /certs
port=$(docker port "$container" 9000/tcp)
curl --fail --silent --show-error --retry 8 --retry-all-errors --retry-delay 2 --retry-max-time 24 --max-time 4 \
  --cacert "$scratch/tls/public.crt" "https://localhost:${port##*:}/minio/health/live"
echo 'PASS: Archive entry points and trusted MinIO HTTPS health check.'
