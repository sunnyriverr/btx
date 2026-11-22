#!/usr/bin/env bash
set -euo pipefail
test "$#" -eq 2 && test "$1" = --execute
test "$(uname -s):$(uname -m)" = Linux:x86_64
test "$(id -u)" -ne 0
fixture=$(cd -- "$(dirname -- "$0")" && pwd)
# Staging directory contains only inputs from the approved isolated runner.
stage=$(cd -- "$2" && pwd)
cd "$stage"
test -f product/contrib/swapnet/swapnet/evm.py
test "$(git -C product rev-parse HEAD)" = f9ba112822c0089ae2fc3bb5f71e1a28c7cf0302
git -C product diff --quiet HEAD --
umask 077
test -x old/btx-0.34.16/bin/btxd && test -x new/btxd && test -x tools/anvil
sha256sum --check <<EOF
9bbfff065299b3d6e863ecdeb0e54917788c1c0395cfa1d2b61bc40bf364932b  old-release.tar.gz
4107e66f5122d69011337d342ebd30ff2eefdb4da3de75e6750fde099a750730  new/btxd
2db95cc3d8310876264eda6cfeed613173b7c8b60041db8e630b954e6af1a6b8  new/btx-cli
cc6b5239d4c0cacc6a5086619eee1e4a9ec6aa7a21bf1df631ebaa7816139d16  tools/anvil
4789e6b06d33de4194926b9356c26374ee5138181a1f2882e9e190da279cf62c  $fixture/inputs/SwapNetHTLC.json
EOF
# Check the staged release tree against the verified archive before using its launcher.
python3 - <<'VERIFY'
import os
from pathlib import Path
import tarfile
root = Path('old').resolve()
with tarfile.open('old-release.tar.gz', 'r|gz') as archive:
    for entry in archive:
        path = root / entry.name
        if not path.parent.resolve().is_relative_to(root):
            raise ValueError(entry.name)
        if entry.issym():
            assert path.is_symlink() and os.readlink(path) == entry.linkname
            assert path.resolve().is_relative_to(root)
        elif entry.isdir():
            assert path.is_dir() and not path.is_symlink()
        elif entry.isfile():
            assert path.is_file() and not path.is_symlink()
            assert path.stat().st_size == entry.size
            assert path.stat().st_mode & 0o111 == entry.mode & 0o111
            with path.open('rb') as actual, archive.extractfile(entry) as expected:
                for block in iter(lambda: expected.read(1048576), b''):
                    assert actual.read(len(block)) == block, entry.name
        elif entry.islnk():
            assert path.samefile(root / entry.linkname)
        else:
            raise ValueError(entry.name)
VERIFY
test ! -e records/settle
mkdir -p records
scratch=$(mktemp -d "$stage/btxeth.XXXXXXXX")
test "$(df -Pk "$scratch" | awk 'NR==2 {print $4}')" -gt 2621440
read -r oldhash _ < <(sha256sum old/btx-0.34.16/bin/btxd)
port=$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1])')
export BTX_OLD="$stage/old/btx-0.34.16/bin/btxd" BTX_OLD_SHA256="$oldhash"
export BTX_NEW="$stage/new/btxd" BTX_NEW_SHA256=4107e66f5122d69011337d342ebd30ff2eefdb4da3de75e6750fde099a750730
export CONTRACT_ARTIFACT="$fixture/inputs/SwapNetHTLC.json" ANVIL_URL="http://127.0.0.1:$port"
unset GH_TOKEN GITHUB_TOKEN LD_PRELOAD PYTHONPATH PYTHONHOME
export NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost
mkdir "$scratch/anvil-home"
HOME="$scratch/anvil-home" "$stage/tools/anvil" --host 127.0.0.1 --port "$port" --slots-in-an-epoch 1 --quiet >records/anvil.log 2>&1 &
anvil=$!
cleanup() {
    if kill -0 "$anvil" 2>/dev/null; then kill "$anvil"; fi
    wait "$anvil" || test "$?" -eq 143
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
for _ in {1..40}; do
    kill -0 "$anvil"
    if curl --noproxy '*' --silent --fail --max-time 1 -H 'Content-Type: application/json' \
        -d '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}' "$ANVIL_URL" |
        python3 -c 'import json,sys; sys.exit(json.load(sys.stdin).get("result") != "0x7a69")' 2>/dev/null; then
        ready=1
        break
    fi
    sleep 0.25
done
test "${ready:-0}" -eq 1
timeout --kill-after=20s 600s python3 -B -u "$fixture/upgrade.py" "$scratch" settle
kill -0 "$anvil"
