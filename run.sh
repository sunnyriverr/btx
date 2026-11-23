#!/usr/bin/env bash
set -euo pipefail
[[ "$(uname -sm)" == 'Linux x86_64' ]]
. /etc/os-release
[[ "$VERSION_ID" == '24.04' ]]
records="$GITHUB_WORKSPACE/records"
mkdir "$records"
root=$(mktemp -d /tmp/btx-s1-snap.XXXXXXXX)
df -Pk "$root" | tee "$records/disk.txt"
[[ "$(df -Pk "$root" | awk 'NR==2 {print $4}')" -ge 8388608 ]]
export HOME="$root/home"
mkdir "$HOME" "$root/assets"
base=https://github.com/btxchain/btx/releases/download/v0.34.17
archive=btx-0.34.17-x86_64-linux-gnu.tar.gz
for file in "$archive" btx-release-manifest.json SHA256SUMS; do
    curl -fsSL --retry 2 --max-time 90 "$base/$file" -o "$root/assets/$file"
done
(
    cd "$root/assets"
    sha256sum -c - <<'SUMS'
e93be7a55b6f786ec0147aa7b02c06fdaf8e7a04dd1d748a47b2ccd9662a4d9d  btx-0.34.17-x86_64-linux-gnu.tar.gz
ed9787b6dff5b85686e7b9b2741c1c292a02484dd58188241e22f282756067f8  btx-release-manifest.json
392b3602d39568ce5e5e2512ba5dff59acecec1a50a99b41a4b548f1681fb623  SHA256SUMS
SUMS
    [[ "$(stat -c %s "$archive")" == 124582532 ]]
    jq -e '.source_commit == "932a0238c70705b28ea344a7929cee09ada314c8" and .signature_file == null' btx-release-manifest.json
    cp btx-release-manifest.json SHA256SUMS "$records/"
) | tee "$records/intake.log"
commit=932a0238c70705b28ea344a7929cee09ada314c8
curl -fsSL --max-time 45 "https://raw.githubusercontent.com/btxchain/btx/$commit/contrib/faststart/btx-agent-setup.py" -o "$root/installer.py"

snapshot=assumeutxo-228000.dat
curl -fsSL --max-time 75 "https://github.com/btxchain/btx/releases/download/assumeutxo-228000/$snapshot" -o "$root/$snapshot"
printf '%s  %s\n' 45392da4550a66ccd4ed949cc0e47cb2197dbf2fd238f79367c921adf8508890 "$root/$snapshot" | sha256sum -c | tee "$records/snapshot-hash.txt"
python3 -B "$root/installer.py" --release-manifest "$root/assets/btx-release-manifest.json" \
    --asset-base-url "$root/assets" --install-dir "$root/installed" --cache-dir "$root/cache" \
    --platform linux-x86_64 --allow-unsigned-release --no-start-daemon --json > "$records/install.json"
python3 -B observe.py "$root" "$records"
