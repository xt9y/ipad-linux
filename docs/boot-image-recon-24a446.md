# J407 boot image recon — host-side first pass (24A446)

Source: raw `iBoot.j407.RELEASE` payload (the unified iBSS/iBEC/LLB/iBoot image, build tag `mBoot-20457.2.37`), analyzed offline outside the repository. This report contains only digest prefixes and content strings — no device-unique values exist in a bootloader image anyway.

```text
## header
size: 2255320 bytes
sha256: dc3cb25f29f25645 (prefix)
first-32-bytes: 1f211cd5df3f03d502113cd542005eb2420065b202111cd5df3f03d500000090
tail-16-bytes: 05000000000000000100000000000000

## strings
total printable tokens: 1953 (unique 1348)

## build identities
  mBoot-20457.2.37

## keyword corpus
  [  1] getenv: getenv
  [  1] setenv: setenv
  [ 10] usb: arm-io/usb-complex; arm-io/usb-complex/usb-device; force-usb-power; rsm-usb; usb-device; usb-drd0; usb-drd1; usb-hi-current; usb-otg0; usb-otg1
  [ 18] dart: arm-io/dart-; dart-acio0; dart-acio1; dart-ane; dart-aop; dart-apciec0; dart-apciec1; dart-ave; dart-dcp; dart-dcpext; dart-disp0; dart-dispext0; dart-id; dart-isp; dart-sio; dart-tunables-instance-; dart-usb0; dart-usb1
  [  2] pmgr: arm-io/pmgr; arm-io/pmgr-child
  [  2] secure: secure-boot; secure-boot-hashes
  [  2] aes: gid-aes-key; uid-aes-key
  [  1] malloc: malloc
  [ 54] boot: auto-boot; auto-boot-once; battery-force-boot; boot-adapter-id; boot-args; boot-battery-state; boot-breadcrumbs; boot-command; boot-device; boot-ios-diagnostics; boot-manifest-hash; boot-nonce; boot-nonce-hash-method; boot-object-manifests; boot-partition; boot-path; boot-ramdisk; boot-reason; boot-stage; boot-type; boot-voltage; boot/OS.dmg; boot/active; boot/applelogo
  [  7] debug: arm-io/cpu-debug-interface; debug-enabled; debug-soc; debug-uarts; debug-wait-start; dev-unset-debug-enabled; enable-auth-debug

## short identifiers (frequency >= 2, top 60)
   40x single
   22x struct
   15x failed
   14x calibration
   13x invalid
   10x called
    9x passed
    8x string
    8x sysconfig
    8x upgrade
    7x external
    7x parity
    7x terminated_by
    7x version
    6x manifest
    6x tunables
    6x uint32_t
    5x access
    5x cannot
    5x expected
    5x memory
    5x recover
    5x source
    5x synchronous
    4x channel
    4x command
    4x defined
    4x deleted
    4x firmware
    4x fsboot
    4x image_count
    4x image_offset
    4x interrupt
    4x length
    4x optmask
    4x provided
    4x reached
    4x section
    4x setpicture
    4x uint8_t
    4x unknown
    3x button
    3x common
    3x config
    3x counted_by
    3x decode
    3x exception
    3x failing
    3x flipbook
    3x offset
    3x repair
    3x unsupported
    2x abcdef
    2x aborting
    2x address
    2x apciec0
    2x apciec1
    2x battery
    2x bytemode
    2x chained

## entropy (48 KiB windows)
  windows: 46 high-entropy(>3.0): 41 low: 5
```
