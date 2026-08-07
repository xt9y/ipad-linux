#!/bin/sh
set -eu

DTB="${1:?usage: check-j407-dtb.sh <t8103-j407.dtb>}"

need_node() {
    node="$1"
    fdtget -p "$DTB" "$node" >/dev/null
}

need_prop() {
    node="$1"
    prop="$2"
    fdtget "$DTB" "$node" "$prop" >/dev/null
}

need_string() {
    node="$1"
    prop="$2"
    expected="$3"
    actual="$(fdtget -t s "$DTB" "$node" "$prop")"
    [ "$actual" = "$expected" ] || {
        echo "$node/$prop: expected '$expected', got '$actual'" >&2
        exit 1
    }
}

# Board identity and m1n1 kboot's mandatory top-level data.
need_prop / compatible
need_prop / model
need_node /chosen
need_prop /chosen stdout-path
need_node /memory@800000000
need_prop /memory@800000000 reg
need_node /cpus

# m1n1 kboot patches all T8103 spin-table release slots in place.
for cpu in 0 1 2 3 10100 10101 10102 10103; do
    need_node "/cpus/cpu@$cpu"
    need_prop "/cpus/cpu@$cpu" cpu-release-addr
done

# First-boot diagnostics: UART plus an optional firmware framebuffer target.
need_node /soc/serial@235200000
need_prop /soc/serial@235200000 compatible
need_node /chosen/framebuffer@0
need_prop /chosen/framebuffer@0 compatible
need_prop /chosen/framebuffer@0 reg
need_prop /chosen/framebuffer@0 status

# J407 storage addresses/IRQ/SART independently match the public Apple ADT.
need_node /soc/mbox@277408000
need_node /soc/sart@27bc50000
need_node /soc/nvme@27bcc0000
need_prop /soc/nvme@27bcc0000 reg
need_prop /soc/nvme@27bcc0000 interrupts
need_prop /soc/nvme@27bcc0000 mboxes
need_prop /soc/nvme@27bcc0000 apple,sart

# J407's BCM4387 combo radio is PCIe port00 function 0/1. Resolve through
# aliases because m1n1 uses these names for MAC/calibration patching too.
need_prop /aliases wifi0
need_prop /aliases bluetooth0
wifi_path="$(fdtget -t s "$DTB" /aliases wifi0)"
bt_path="$(fdtget -t s "$DTB" /aliases bluetooth0)"
need_node "$wifi_path"
need_node "$bt_path"
need_string "$wifi_path" compatible "pci14e4,4433"
need_string "$wifi_path" brcm,board-type "apple,lycheea"
need_string "$bt_path" compatible "pci14e4,5f71"
need_string "$bt_path" brcm,board-type "apple,lycheea"
need_prop "$wifi_path" local-mac-address
need_prop "$wifi_path" apple,antenna-sku
need_prop "$bt_path" local-bd-address

printf 'J407 DTB contract OK: %s\n' "$DTB"
