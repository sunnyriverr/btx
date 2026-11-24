#!/usr/bin/env bash
set -euo pipefail
[[ "$(uname -sm)" == 'Linux x86_64' ]]
. /etc/os-release
[[ "$VERSION_ID" == '24.04' ]]
records="$GITHUB_WORKSPACE/records"
mkdir "$records"
root=$(mktemp -d /tmp/btx-s2-18d0.XXXXXXXX)
trap 'rm -rf -- "$root"' EXIT
export HOME="$root/home"
mkdir "$HOME" "$root/assets" "$root/extracted"
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
    jq -e '.source_commit == "18d0b7ff5337c2768f5f5e06c674d8c8898bedad" and .signature_file == null and any(.archives[]; .sha256 == "5b1a62706466f1ab42ca36309b7c63653c8aeb8d57acb86a406240596e02b256")' btx-release-manifest.json
    cp btx-release-manifest.json SHA256SUMS "$records/"
) | tee "$records/intake.log"
python3 -B - "$root/assets/$archive" "$root/extracted" <<'PY'
import sys
import tarfile
with tarfile.open(sys.argv[1]) as bundle:
    bundle.extractall(sys.argv[2], filter='data')
PY
package="$root/extracted/btx-0.34.17"
test -x "$package/bin/btxd"
(
    cd "$package"
    sha256sum bin/{btxd,btx-cli,btx-modeld} libexec/{btxd.real,btx-cli.real,btx-modeld.real}
    LC_ALL=C strings libexec/btxd.real | grep -m1 '18d0b7ff5337' > "$records/embedded-revision.txt" || test -s "$records/embedded-revision.txt"
) | tee "$records/binaries.sha256"
timeout --kill-after=40s 11m python3 -B observe.py "$package" "$records/native"
