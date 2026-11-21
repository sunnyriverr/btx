#!/bin/sh
set -eu

mount --make-rprivate /
mount -t cgroup2 cgroup2 /sys/fs/cgroup
root=/sys/fs/cgroup
group=$root/btx-governor-912
controller_added=0
group_created=0
cleanup() {
    if [ "$group_created" = 1 ]; then
        test ! -d "$group/child" || rmdir "$group/child" || return 1
        rmdir "$group" || return 1
    fi
    if [ "$controller_added" = 1 ]; then
        printf '%s\n' -memory > "$root/cgroup.subtree_control" || return 1
    fi
    echo cleanup_complete
}
trap cleanup EXIT
case " $(cat "$root/cgroup.subtree_control") " in
    *" memory "*) ;;
    *) printf '%s\n' +memory > "$root/cgroup.subtree_control"
       controller_added=1 ;;
esac
mkdir "$group"
group_created=1
echo 268435456 > "$group/memory.max"
echo 67108864 > "$group/memory.swap.max"

printf '%s\n' '{"on_ac":true,"gpu_utilization_pct":0}' > signals.json
export BTX_GOV_SIGNALS_FILE="$PWD/signals.json"
export BTX_GOV_NVIDIA_SAMPLE=0

sample() {
    name=$1
    host_swap_free=$2
    target=$3
    host_ram_available=$4
    echo "case=$name host_swap_free_kib=$host_swap_free host_ram_available_kib=$host_ram_available"
    printf 'MemTotal: 8388608 kB\nMemAvailable: %s kB\nSwapTotal: 1048576 kB\nSwapFree: %s kB\n' \
        "$host_ram_available" "$host_swap_free" > meminfo
    mount --bind "$PWD/meminfo" /proc/meminfo
    cmp meminfo /proc/meminfo
    sh -eu -c '
        group=$1
        if [ "$group" != /sys/fs/cgroup ]; then
            echo "$$" > "$group/cgroup.procs"
        fi
        cat /proc/self/cgroup
        for key in memory.max memory.current memory.swap.max memory.swap.current; do
            if [ -r "$group/$key" ]; then
                printf "%s=" "$key"
                cat "$group/$key"
            fi
        done
        exec "$2"
    ' sh "$target" "$binary"
    umount /proc/meminfo
}
counter() {
    printf '%s\n' "$2" > counter
    mount --bind "$PWD/counter" "$1"
}

for binary in ./before ./after; do
    echo "binary=$binary"
    sample healthy 524288 "$group" 6291456
    sample mismatch 52428 "$group" 6291456
    # Two genuine controller signals at the production read boundary,
    # without exhausting memory or enabling swap on the guest.
    counter "$group/memory.current" 260046848
    sample container_ram 524288 "$group" 6291456
    umount "$group/memory.current"
    counter "$group/memory.swap.current" 66060288
    sample container_swap 524288 "$group" 6291456
    umount "$group/memory.swap.current"

    echo 0 > "$group/memory.swap.max"
    sample zero_swap_limit 52428 "$group" 6291456
    echo max > "$group/memory.swap.max"
    sample unlimited_swap_fallback 52428 "$group" 6291456
    echo 67108864 > "$group/memory.swap.max"

    sample root_fallback_healthy 524288 "$root" 6291456
    sample root_fallback_pressure 52428 "$root" 6291456
    sample host_ram_pressure 524288 "$group" 524288

    echo +memory > "$group/cgroup.subtree_control"
    mkdir "$group/child"
    counter "$group/memory.current" 260046848
    echo ancestor_memory_current="$(cat "$group/memory.current")"
    sample ancestor_ram 524288 "$group/child" 6291456
    umount "$group/memory.current"
    rmdir "$group/child"
    echo -memory > "$group/cgroup.subtree_control"
done
