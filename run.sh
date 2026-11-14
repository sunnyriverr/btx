#!/usr/bin/env bash
set -euo pipefail
mkdir -p records
exec > >(tee -a records/run.log) 2>&1
curl -fsSL --max-time 240 --retry 2 -H "Authorization: Bearer $GH_TOKEN" https://api.github.com/repos/sunnyriverr/btx/actions/artifacts/14095850633/zip -o "$RUNNER_TEMP/binaries.zip"
echo "60cdff188dcc6642125b7ebac17803c81c33bae21c109dfd41744198240305b7  $RUNNER_TEMP/binaries.zip" | sha256sum -c -
python3 - <<'PY'
import zipfile,os,pathlib,configparser
with zipfile.ZipFile(os.environ['RUNNER_TEMP']+'/binaries.zip') as z:
 for n in z.namelist():
  p=pathlib.PurePosixPath(n);assert not p.is_absolute() and '..' not in p.parts
 z.extractall('.')
p=pathlib.Path('obj/test/config.ini');c=configparser.ConfigParser();c.read(p);c['environment']['SRCDIR']=str(pathlib.Path('product').resolve());c['environment']['BUILDDIR']=str(pathlib.Path('obj').resolve());c['environment']['RPCAUTH']=str(pathlib.Path('product/share/rpcauth/rpcauth.py').resolve())
with p.open('w') as f:c.write(f)
PY
sha256sum -c expected.sha256
sha256sum -c candidate/binaries.sha256
cp candidate/btx-modeld obj/bin/btx-modeld
chmod +x obj/bin/{btxd,btx-cli,btx-modeld}
ldd obj/bin/btx-modeld | tee records/ldd.txt
! grep -F 'not found' records/ldd.txt
sudo apt-get update -qq
sudo apt-get install -y -qq libevent-dev libzmq3-dev python3-cryptography
image=btx-normal-recovery:2025-04-22
mkdir -p minio-image
tag=RELEASE.2025-04-22T22-12-26Z
curl -fsSL --max-time 120 --retry 2 "https://github.com/minio/minio/releases/download/$tag/minio.linux-amd64.$tag" -o minio-image/minio
(cd minio-image && echo '53e2a2cb16c5366ea6fbbc479c19ddb4c6a0948273e752f740fb1fbf27bb817c  minio' | sha256sum -c -)
chmod +x minio-image/minio
printf 'FROM scratch\nCOPY minio /minio\nENV HOME=/root\nENTRYPOINT ["/minio"]\n' > minio-image/Dockerfile
docker build -t "$image" minio-image
export BTX_MINIO_IMAGE BTXMODELD
BTX_MINIO_IMAGE=$(docker image inspect --format '{{.Id}}' "$image")
BTXMODELD="$PWD/obj/bin/btx-modeld"
docker run --rm "$image" --version | tee records/minio-version.txt
cp feature_modelnet_minio.py product/test/functional/feature_modelnet_minio.py
cp strict_minio.py product/test/functional/strict_minio.py
cp controls.py product/test/functional/cloud_controls.py
run_case() {
 local label="$1" script="$2"
 set +e
 timeout --kill-after=20s 12m /usr/bin/python3 "product/test/functional/$script" --configfile="$PWD/obj/test/config.ini" --tmpdir="$RUNNER_TEMP/$label" --nocleanup > "records/$label.log" 2>&1
 local status=$?
 set -e
 cat "records/$label.log"
 printf '%s\n' "$status" > "records/$label.exit"
 for result in cloud-controls.json cloud-controls-partial.json; do
  if test -f "$RUNNER_TEMP/$label/$result"; then cp "$RUNNER_TEMP/$label/$result" records/; fi
 done
 return "$status"
}
run_case full-cloud strict_minio.py
grep -F MINIO_RECOVERY_BYTE_IDENTICAL records/full-cloud.log
run_case cloud-negative cloud_controls.py
python3 -c "import json;r=json.load(open('records/cloud-controls.json'));assert len(r)==2 and all(x['live_pieces']==0 and x['response'].get('status')!='local' for x in r);print('NATIVE_CONTROLS_VERIFIED')"
