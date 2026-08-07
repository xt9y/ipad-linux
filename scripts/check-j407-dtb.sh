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

forbid_prop() {
    node="$1"
    prop="$2"
    if fdtget "$DTB" "$node" "$prop" >/dev/null 2>&1; then
        echo "J407 DTB: unexpected $node/$prop" >&2
        exit 1
    fi
}

need_string() {
    node="$1"
    prop="$2"
    expected="$3"
    actual="$(fdtget -t s "$DTB" "$node" "$prop")"
    [ "$actual" = "$expected" ] || {
        echo "J407 DTB: $node/$prop='$actual', expected='$expected'" >&2
        exit 1
    }
}

need_hex() {
    node="$1"
    prop="$2"
    expected="$3"
    actual="$(fdtget -t x "$DTB" "$node" "$prop")"
    [ "$actual" = "$expected" ] || {
        echo "J407 DTB: $node/$prop='$actual', expected='$expected'" >&2
        exit 1
    }
}

need_status() {
    node="$1"
    expected="$2"
    actual="$(fdtget -t s "$DTB" "$node" status)"
    [ "$actual" = "$expected" ] || {
        echo "J407 DTB: $node/status='$actual', expected='$expected'" >&2
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
need_status /soc/serial@235200000 okay
need_node /chosen/framebuffer@0
need_prop /chosen/framebuffer@0 compatible
need_prop /chosen/framebuffer@0 reg
need_status /chosen/framebuffer@0 disabled

# J407 storage addresses/IRQ/SART independently match the public Apple ADT.
need_node /soc/mbox@277408000
need_node /soc/iommu@27bc50000
need_node /soc/nvme@27bcc0000
need_prop /soc/nvme@27bcc0000 reg
need_prop /soc/nvme@27bcc0000 interrupts
need_prop /soc/nvme@27bcc0000 mboxes
need_prop /soc/nvme@27bcc0000 apple,sart

# J407 contains one verified T8103 USB0/DART/ATC-PHY path. The second T8103
# path is absent from the public J407 ADT and must remain disabled.
need_status /soc/usb@382280000 okay
need_status /soc/iommu@382f00000 okay
need_status /soc/iommu@382f80000 okay
need_status /soc/phy@383000000 okay
need_status /soc/usb@502280000 disabled
need_status /soc/iommu@502f00000 disabled
need_status /soc/iommu@502f80000 disabled
need_status /soc/phy@503000000 disabled

# J407's public ADT identifies one CD3217 directly under i2c0 at 0x38.
# The Apple IRQ encoding is not yet translated, so preserve the intentional
# polling-only contract and fail CI if a guessed interrupt sneaks into the DTS.
hpm=/soc/i2c@235010000/usb-pd@38
need_node "$hpm"
need_string "$hpm" compatible "apple,cd321x"
need_hex "$hpm" reg "38"
forbid_prop "$hpm" interrupts
forbid_prop "$hpm" interrupt-parent

# J407 APCIE port0 is verified from the public ADT. PERST# resolves to GPIO
# 152 (matching t8103.dtsi), and the two functions are the BCM4387 combo chip.
need_status /soc/pcie@690000000 okay
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
