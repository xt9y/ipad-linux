#!/bin/sh
set -eu

CROSS_COMPILE="${CROSS_COMPILE:-aarch64-linux-gnu-}"
OUT="${1:-build/initramfs}"
ROOT="$OUT/root"

rm -rf "$OUT"
mkdir -p "$ROOT" "$ROOT/dev" "$ROOT/proc" "$ROOT/sys" "$ROOT/tmp"

"${CROSS_COMPILE}gcc" \
    -std=c17 -Os -Wall -Wextra -Werror \
    -static -s \
    initramfs/init.c \
    -o "$ROOT/init"

(
    cd "$ROOT"
    find . -print0 | cpio --null -o --format=newc --owner=0:0 2>/dev/null
) | gzip -9 > "$OUT/initramfs.cpio.gz"

printf 'built %s\n' "$OUT/initramfs.cpio.gz"
file "$ROOT/init"
ls -lh "$OUT/initramfs.cpio.gz"
