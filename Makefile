TARGET := build/payload
CC := clang
LD := ld.lld
OBJCOPY := llvm-objcopy
OBJDUMP := llvm-objdump
READELF := llvm-readelf
NM := llvm-nm
PYTHON := python3

PLATFORM := j407
PLATFORM_DIR := src/platform/$(PLATFORM)

INCLUDES := -Isrc/boot -Isrc/adt -Isrc/fdt -Isrc/memory -Isrc/debug -Isrc/arch/aarch64 -I$(PLATFORM_DIR)
CFLAGS := --target=aarch64-none-elf -ffreestanding -fpie -fno-plt -fno-stack-protector -fno-builtin -nostdlib -Wall -Wextra -O2 $(INCLUDES)
ASFLAGS := --target=aarch64-none-elf -ffreestanding -nostdlib
LDFLAGS := -T src/payload/linker.ld -nostdlib

OBJS := \
	build/start.o \
	build/exceptions.o \
	build/exception_report.o \
	build/system.o \
	build/linux_handoff.o \
	build/linux_image.o \
	build/linux_fdt.o \
	build/linux_layout.o \
	build/boot_plan.o \
	build/main.o \
	build/platform.o \
	build/discovery.o \
	build/quiesce.o \
	build/smp_contract.o \
	build/memory.o \
	build/adt.o \
	build/adt_reg.o \
	build/adt_function.o \
	build/fdt.o \
	build/debug.o \
	build/uart.o

all: $(TARGET).elf $(TARGET).bin verify-image $(TARGET).dis

build:
	mkdir -p build

build/start.o: src/payload/start.S | build
	$(CC) $(ASFLAGS) -c $< -o $@

build/exceptions.o: src/arch/aarch64/exceptions.S | build
	$(CC) $(ASFLAGS) -c $< -o $@

build/exception_report.o: src/arch/aarch64/exceptions.c src/arch/aarch64/exceptions.h | build
	$(CC) $(CFLAGS) -c $< -o $@

build/system.o: src/arch/aarch64/system.S | build
	$(CC) $(ASFLAGS) -c $< -o $@

build/linux_handoff.o: src/boot/linux_handoff.S | build
	$(CC) $(ASFLAGS) -c $< -o $@

build/linux_image.o: src/boot/linux_image.c src/boot/linux_image.h | build
	$(CC) $(CFLAGS) -c $< -o $@

build/linux_fdt.o: src/boot/linux_fdt.c src/boot/linux_fdt.h | build
	$(CC) $(CFLAGS) -c $< -o $@

build/linux_layout.o: src/boot/linux_layout.c src/boot/linux_layout.h | build
	$(CC) $(CFLAGS) -c $< -o $@

build/boot_plan.o: src/boot/boot_plan.c src/boot/boot_plan.h | build
	$(CC) $(CFLAGS) -c $< -o $@

build/main.o: src/payload/main.c | build
	$(CC) $(CFLAGS) -c $< -o $@

build/platform.o: $(PLATFORM_DIR)/platform.c $(PLATFORM_DIR)/platform.h | build
	$(CC) $(CFLAGS) -c $< -o $@

build/discovery.o: $(PLATFORM_DIR)/discovery.c $(PLATFORM_DIR)/discovery.h | build
	$(CC) $(CFLAGS) -c $< -o $@

build/quiesce.o: $(PLATFORM_DIR)/quiesce.c $(PLATFORM_DIR)/quiesce.h | build
	$(CC) $(CFLAGS) -c $< -o $@

build/smp_contract.o: $(PLATFORM_DIR)/smp_contract.c $(PLATFORM_DIR)/smp_contract.h | build
	$(CC) $(CFLAGS) -c $< -o $@

build/memory.o: src/memory/memory.c src/memory/memory.h | build
	$(CC) $(CFLAGS) -c $< -o $@

build/adt.o: src/adt/adt.c src/adt/adt.h | build
	$(CC) $(CFLAGS) -c $< -o $@

build/adt_reg.o: src/adt/adt_reg.c src/adt/adt.h | build
	$(CC) $(CFLAGS) -c $< -o $@

build/adt_function.o: src/adt/adt_function.c src/adt/adt_function.h src/adt/adt.h | build
	$(CC) $(CFLAGS) -c $< -o $@

build/fdt.o: src/fdt/fdt.c src/fdt/fdt.h | build
	$(CC) $(CFLAGS) -c $< -o $@

build/debug.o: src/debug/debug.c src/debug/debug.h | build
	$(CC) $(CFLAGS) -c $< -o $@

build/uart.o: src/debug/uart.c src/debug/uart.h | build
	$(CC) $(CFLAGS) -c $< -o $@

$(TARGET).elf: $(OBJS) src/payload/linker.ld
	$(LD) $(LDFLAGS) $(OBJS) -o $@

verify-relocs: $(TARGET).elf
	@! $(READELF) -r $< | grep -q 'R_AARCH64_' || (echo 'error: payload contains runtime relocations' && $(READELF) -r $< && exit 1)

$(TARGET).bin: $(TARGET).elf
	$(OBJCOPY) -O binary $< $@

verify-image: $(TARGET).elf $(TARGET).bin verify-relocs scripts/check-stage2-image.py
	$(PYTHON) scripts/check-stage2-image.py \
		--elf $(TARGET).elf \
		--bin $(TARGET).bin \
		--nm $(NM) \
		--readelf $(READELF)

$(TARGET).dis: $(TARGET).elf
	$(OBJDUMP) -d $< > $@

# Host-side test runner. This mirrors the test suites in the CI workflows
# (.github/workflows/build.yml, layout.yml, tools.yml, firmware-checker.yml)
# so the same checks run locally before commit.
HOSTCC := $(CC)
HOSTCFLAGS := -std=c17 -Wall -Wextra -Werror
ADT_SOURCES := src/adt/adt.c src/adt/adt_reg.c src/adt/adt_function.c
PYTHON_TESTS := \
	tests/pack_m1n1_test.py \
	tests/pack_m1n1_scan_test.py \
	tests/analyze_first_boot_test.py \
	tests/build_hardware_report_test.py \
	tests/verify_first_boot_kit_test.py \
	tests/host_preflight_test.py \
	tests/j407_firmware_test.py \
	tests/j407_firmware_diff_test.py \
	tests/check_j407_firmware_test.py \
	tests/z2fw_test.py \
	tests/dfu_fuzz_test.py \
	tests/boot_image_recon_test.py \
	tests/boot_image_disasm_test.py

test: host-tests $(PYTHON_TESTS)

$(PYTHON_TESTS):
	$(PYTHON) -m unittest -v $@

host-tests:
	mkdir -p build
	$(HOSTCC) $(HOSTCFLAGS) -Isrc/adt tests/adt_test.c src/adt/adt.c -o build/adt_test
	./build/adt_test
	$(HOSTCC) $(HOSTCFLAGS) -Isrc/adt tests/adt_reg_test.c src/adt/adt.c src/adt/adt_reg.c -o build/adt_reg_test
	./build/adt_reg_test
	$(HOSTCC) $(HOSTCFLAGS) -Isrc/adt tests/adt_function_test.c src/adt/adt_function.c src/adt/adt.c -o build/adt_function_test
	./build/adt_function_test
	$(HOSTCC) $(HOSTCFLAGS) -Isrc/adt tests/adt_clock_test.c src/adt/adt_clock.c src/adt/adt.c -o build/adt_clock_test
	./build/adt_clock_test
	$(HOSTCC) $(HOSTCFLAGS) -Isrc/adt -I$(PLATFORM_DIR) tests/j407_discovery_test.c $(PLATFORM_DIR)/discovery.c $(ADT_SOURCES) -o build/j407_discovery_test
	./build/j407_discovery_test
	$(HOSTCC) $(HOSTCFLAGS) -Isrc/boot tests/boot_info_test.c -o build/boot_info_test
	./build/boot_info_test
	$(HOSTCC) $(HOSTCFLAGS) -Isrc/boot tests/m1n1_handoff_test.c src/boot/m1n1_handoff.c -o build/m1n1_handoff_test
	./build/m1n1_handoff_test
	$(HOSTCC) $(HOSTCFLAGS) -Isrc/boot -Isrc/memory tests/linux_boot_test.c src/boot/linux_image.c src/boot/boot_plan.c src/memory/memory.c -o build/linux_boot_test
	./build/linux_boot_test
	$(HOSTCC) $(HOSTCFLAGS) -Isrc/fdt tests/fdt_test.c src/fdt/fdt.c -o build/fdt_test
	./build/fdt_test build/test.dtb
	dtc -I dtb -O dts build/test.dtb -o build/test.dts
	grep -q 'apple,j407' build/test.dts
	$(HOSTCC) $(HOSTCFLAGS) -Isrc/boot -Isrc/fdt -Isrc/memory tests/linux_fdt_test.c src/boot/linux_fdt.c src/fdt/fdt.c src/memory/memory.c -o build/linux_fdt_test
	./build/linux_fdt_test
	$(HOSTCC) $(HOSTCFLAGS) -Isrc/boot -Isrc/fdt -Isrc/memory -I$(PLATFORM_DIR) tests/j407_smp_test.c $(PLATFORM_DIR)/smp_contract.c src/memory/memory.c -o build/j407_smp_test
	./build/j407_smp_test
	$(HOSTCC) $(HOSTCFLAGS) -Isrc/boot -Isrc/memory tests/linux_layout_test.c src/boot/linux_layout.c src/boot/boot_plan.c src/memory/memory.c -o build/linux_layout_test
	./build/linux_layout_test

verify: verify-image test

clean:
	rm -rf build

.PHONY: all clean verify-relocs verify-image verify test host-tests $(PYTHON_TESTS)
