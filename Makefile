TARGET := build/payload
CC := clang
LD := ld.lld
OBJCOPY := llvm-objcopy
OBJDUMP := llvm-objdump
READELF := llvm-readelf

PLATFORM := j407
PLATFORM_DIR := src/platform/$(PLATFORM)

INCLUDES := -Isrc/boot -Isrc/adt -Isrc/memory -I$(PLATFORM_DIR)
CFLAGS := --target=aarch64-none-elf -ffreestanding -fpie -fno-plt -fno-stack-protector -fno-builtin -nostdlib -Wall -Wextra -O2 $(INCLUDES)
ASFLAGS := --target=aarch64-none-elf -ffreestanding -nostdlib
LDFLAGS := -T src/payload/linker.ld -nostdlib

OBJS := \
	build/start.o \
	build/exceptions.o \
	build/main.o \
	build/platform.o \
	build/memory.o \
	build/adt.o

all: $(TARGET).elf verify-relocs $(TARGET).bin $(TARGET).dis

build:
	mkdir -p build

build/start.o: src/payload/start.S | build
	$(CC) $(ASFLAGS) -c $< -o $@

build/exceptions.o: src/arch/aarch64/exceptions.S | build
	$(CC) $(ASFLAGS) -c $< -o $@

build/main.o: src/payload/main.c | build
	$(CC) $(CFLAGS) -c $< -o $@

build/platform.o: $(PLATFORM_DIR)/platform.c $(PLATFORM_DIR)/platform.h | build
	$(CC) $(CFLAGS) -c $< -o $@

build/memory.o: src/memory/memory.c src/memory/memory.h | build
	$(CC) $(CFLAGS) -c $< -o $@

build/adt.o: src/adt/adt.c src/adt/adt.h | build
	$(CC) $(CFLAGS) -c $< -o $@

$(TARGET).elf: $(OBJS) src/payload/linker.ld
	$(LD) $(LDFLAGS) $(OBJS) -o $@

verify-relocs: $(TARGET).elf
	@! $(READELF) -r $< | grep -q 'R_AARCH64_' || (echo 'error: payload contains runtime relocations' && $(READELF) -r $< && exit 1)

$(TARGET).bin: $(TARGET).elf
	$(OBJCOPY) -O binary $< $@

$(TARGET).dis: $(TARGET).elf
	$(OBJDUMP) -d $< > $@

clean:
	rm -rf build

.PHONY: all clean verify-relocs
