#!/usr/bin/env bash
set -euo pipefail
. /etc/os-release
test "$VERSION_ID" = 22.04
test "$(uname -m)" = x86_64
export DEBIAN_FRONTEND=noninteractive
keyring=/usr/share/keyrings/ubuntu-archive-keyring.gpg
ca=/ubuntu-host-ca.pem
test -r "$keyring"
test -r "$ca"
mkdir -p records
exec > >(tee records/ubuntu-prerequisites.log) 2>&1
sources=$(mktemp --suffix=.sources)
chmod 644 "$sources"
trap 'rm -f "$sources"' EXIT
apt_opts=(-o "Dir::Etc::sourcelist=$sources" -o Dir::Etc::sourceparts=-
          -o Acquire::Retries=0 -o Acquire::https::Timeout=15 -o "Acquire::https::CAInfo=$ca")
packages=(ca-certificates curl git build-essential cmake ninja-build pkg-config python3 perl
          iproute2 libboost-dev libevent-dev libsqlite3-dev libzmq3-dev libqrencode-dev
          qt6-base-dev qt6-base-dev-tools qt6-tools-dev qt6-tools-dev-tools qt6-l10n-tools)
deadline=$((SECONDS + 570))
selected=
for mirror in https://mirrors.edge.kernel.org/ubuntu/ https://mirror.math.princeton.edu/pub/ubuntu/ https://mirrors.mit.edu/ubuntu/; do
    remaining=$((deadline - SECONDS))
    (( remaining >= 90 )) || break
    printf 'Checking signed Jammy indexes at %s\n' "$mirror"
    printf '%s\n' 'Types: deb' "URIs: $mirror" 'Suites: jammy jammy-updates jammy-security' \
        'Components: main universe' "Signed-By: $keyring" > "$sources"
    if ! timeout --kill-after=5s 55s apt-get "${apt_opts[@]}" -o APT::Update::Error-Mode=any update; then
        continue
    fi
    remaining=$((deadline - SECONDS - 5))
    (( remaining >= 30 )) || break
    budget=$((remaining < 135 ? remaining : 135))
    if timeout --kill-after=5s "${budget}s" apt-get "${apt_opts[@]}" --download-only install \
            -y --no-install-recommends "${packages[@]}"; then
        selected=$mirror
        break
    fi
done
if [[ -z "$selected" ]]; then
    printf '%s\n' 'No signed mirror completed the dependency download.' >&2
    exit 1
fi
timeout --kill-after=5s 150s apt-get "${apt_opts[@]}" --no-download install \
    -y --no-install-recommends "${packages[@]}"
dpkg-query -W "${packages[@]}" > records/ubuntu-prerequisite-packages.txt
printf '%s\n' "$selected" > records/ubuntu-prerequisite-mirror.txt
