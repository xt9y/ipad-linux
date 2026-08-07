# Boot-chain research

## Working model

The project currently models the target boot flow as:

```text
BootROM
  -> iBoot / Apple secure boot stages
  -> unknown future execution mechanism
  -> custom bootstrap
  -> m1n1-derived or compatible loader
  -> Linux
```

## Important distinction

Apple Silicon Macs expose a supported alternate-OS boot-policy path that projects such as Asahi Linux can use. iPadOS devices do not expose the same user-authorized custom-kernel flow.

Therefore the first unsolved problem is not Linux itself. It is obtaining controlled execution at a privilege level and boot stage that can hand ownership of the machine to our own loader.

## Unknowns to resolve

- Exact target iPad model identifier
- Board identifier
- SoC/platform identifier
- Installed iPadOS version
- BootROM/iBoot behavior for that device generation
- Recovery/DFU USB behavior
- Whether any public vulnerability provides sufficiently early arbitrary code execution
- Memory map available to a bootstrap
- Device tree format and availability at the prospective entry point
- Required exception level for Linux handoff

## Research rule

Do not treat jailbreak-level userspace execution as equivalent to a native Linux boot path. Each proposed entry mechanism must be evaluated by the privilege level, boot stage, persistence properties, hardware state, and ability to replace or bypass XNU.
