#!/usr/bin/env bash
set -euo pipefail

archive=${1:?Pass the retained Linux CPU archive}
work_dir=${2:?Pass an empty disposable Linux directory}
minio_image=${BTX_MINIO_IMAGE:?Set BTX_MINIO_IMAGE to the pinned MinIO image reference}

if [[ $(uname -s) != Linux || $(uname -m) != x86_64 ]]; then
    echo "This archive requires an x86-64 Linux runner." >&2
    exit 2
fi
if [[ -n $(find "$work_dir" -mindepth 1 -maxdepth 1 -print -quit) ]]; then
    echo "The disposable directory must be empty." >&2
    exit 2
fi
digest=$(sha256sum "$archive")
if [[ ${digest%% *} != 1e60e4be26cc1ae14045e5299e891f8b30d8b7db0e24cf881bd2eb68811aaa4e ]]; then
    echo "Archive digest mismatch." >&2
    exit 2
fi
tar -xzf "$archive" -C "$work_dir"
root=$work_dir/btx-0.34.17
test -x "$root/libexec/btx-modeld.real"
ldd -v "$root/libexec/btx-modeld.real" > "$work_dir/modeld-loader.log" 2>&1
if grep -Fq 'not found' "$work_dir/modeld-loader.log"; then
    cat "$work_dir/modeld-loader.log" >&2
    exit 1
fi
timeout 15 "$root/bin/btx-modeld" -version
timeout 15 "$root/bin/btxd" -version
timeout 15 "$root/bin/btx-cli" -version
docker image inspect --format '{{.Id}}' "$minio_image"
echo "Archive, Linux loader, entry points and local MinIO image verified."
