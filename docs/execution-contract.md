# Execution contract

The payload must not depend on a particular iPadOS release, jailbreak, kernel exploit, iBoot exploit, recovery primitive, or future loader implementation.

## Entry ABI

The loader enters `_start` with:

```text
x0 = pointer to struct boot_info, or 0 when no contract is available
```

The payload preserves `x0`, establishes its temporary internal stack, and passes the pointer to `kernel_main()`.

`struct boot_info` is versioned and begins with a fixed magic value. A future loader may populate:

- usable RAM base and size
- Apple Device Tree address and size
- loaded image address and size
- current exception level
- state flags such as MMU enabled / ADT available

Unknown fields must be zeroed.

## Exception vectors

`src/arch/aarch64/exceptions.S` provides a correctly aligned EL1 vector table and an installation routine. The payload does **not** install it automatically because executing `MSR VBAR_EL1` is only valid once the caller has established that execution is occurring at a suitable exception level.

## Apple Device Tree

The ADT parser uses the format implemented by Asahi Linux/m1n1:

```text
node:
    u32 property_count
    u32 child_count
    property[property_count]
    node[child_count]

property:
    char name[32]
    u32 encoded_size
    u8 value[encoded_size & 0x7fffffff]
    padding to 4-byte alignment
```

All parser operations are bounded by the ADT size supplied by the loader. The first implementation validates the tree recursively and can retrieve root properties. Node/path lookup will be added once we have a real J407 ADT to test against.

## Current limitation

The raw payload still uses a provisional link/load address and an internal linker-provided stack. Once a real execution primitive exists, the image-loading contract must define the actual load address or the payload must be converted to a relocatable/position-independent form.
