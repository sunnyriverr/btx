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
export MODELNET_TEST_CERT="$scratch/tls/public.crt" MODELNET_TEST_KEY="$scratch/tls/private.key"
export SSL_CERT_FILE="$MODELNET_TEST_CERT"
export BTXMODELD="$scratch/pkg/btx-0.34.17/bin/btx-modeld"
rev=3808e2a978ad93986276aab550b472f3ddfc7ec8
git init -q "$scratch/product"
git -C "$scratch/product" -c http.version=HTTP/1.1 fetch --depth=1 https://github.com/btxchain/btx.git "$rev"
git -C "$scratch/product" checkout -q FETCH_HEAD
git -C "$scratch/product" rev-parse HEAD > evidence/source.txt
fixture="$scratch/product/test/functional/feature_modelnet_minio.py"
python3 adapt_fixture.py "$fixture"
cp https_fixture.py "$(dirname "$fixture")/"
cat > "$scratch/config.ini" <<CFG
[environment]
CLIENT_NAME=BTX
CLIENT_BUGREPORT=https://github.com/btxchain/btx/issues
SRCDIR=$scratch/product
BUILDDIR=$scratch/pkg/btx-0.34.17
EXEEXT=
RPCAUTH=$scratch/product/share/rpcauth/rpcauth.py
[components]
ENABLE_BITCOIND=true
ENABLE_CLI=true
ENABLE_MODELNET=true
CFG
status=0
timeout --kill-after=10s 150s /usr/bin/python3 "$fixture" --configfile="$scratch/config.ini" \
    --bitcoind="$scratch/pkg/btx-0.34.17/bin/btxd" \
    --bitcoincli="$scratch/pkg/btx-0.34.17/bin/btx-cli" --tmpdir="$scratch/state" --nocleanup \
    > evidence/functional.log 2>&1 || status=$?
printf '%s\n' "$status" > evidence/functional-exit.txt
if [[ -f "$scratch/state/partial-retry-result.json" ]]; then
    cp "$scratch/state/partial-retry-result.json" evidence/
fi
if (( status != 0 )); then
    tail -35 evidence/functional.log
    exit "$status"
fi
python3 validate_recovery.py evidence/partial-retry-result.json
