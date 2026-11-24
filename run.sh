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
5b1a62706466f1ab42ca36309b7c63653c8aeb8d57acb86a406240596e02b256  btx-0.34.17-x86_64-linux-gnu.tar.gz
739a2b1c225d7786c2080acdc7d8ddcae7662d2d7e52895b9c317d41ce1e13d7  btx-release-manifest.json
37d58331f27df91772820b9e245ec10214e5be2844b542498a46c5b54ba6d7b9  SHA256SUMS
SUMS
    [[ "$(stat -c %s "$archive")" == 124587880 ]]
    jq -e '.source_commit == "18d0b7ff5337c2768f5f5e06c674d8c8898bedad" and .signature_file == null' btx-release-manifest.json
    cp btx-release-manifest.json SHA256SUMS "$records/"
) | tee "$records/intake.log"
commit=18d0b7ff5337c2768f5f5e06c674d8c8898bedad
curl -fsSL --max-time 45 "https://raw.githubusercontent.com/btxchain/btx/$commit/contrib/faststart/btx-agent-setup.py" -o "$root/installer.py"

snapshot=assumeutxo-228000.dat
curl -fsSL --max-time 75 "https://github.com/btxchain/btx/releases/download/assumeutxo-228000/$snapshot" -o "$root/$snapshot"
printf '%s  %s\n' 45392da4550a66ccd4ed949cc0e47cb2197dbf2fd238f79367c921adf8508890 "$root/$snapshot" | sha256sum -c | tee "$records/snapshot-hash.txt"
python3 -B - "$root" "$archive" > "$records/install.json" <<'PY'
import json
import runpy
import sys
from pathlib import Path
root = Path(sys.argv[1])
archive = root / 'assets' / sys.argv[2]
installer = runpy.run_path(str(root / 'installer.py'))
daemon, cli = installer['install_archive'](archive, root / 'installed', force=False)
print(json.dumps({'btxd': str(daemon), 'btx_cli': str(cli), 'route': 'verified archive, direct install_archive'}))
PY
python3 -B observe.py "$root" "$records"
