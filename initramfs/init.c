#define _POSIX_C_SOURCE 200809L

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/utsname.h>
#include <unistd.h>

static int write_all(int fd, const void *data, size_t size)
{
    const char *p = data;

    while (size) {
        ssize_t written = write(fd, p, size);
        if (written < 0) {
            if (errno == EINTR)
                continue;
            return 0;
        }
        if (written == 0)
            return 0;

        p += (size_t)written;
        size -= (size_t)written;
    }

    return 1;
}

static void make_dir(const char *path)
{
    if (mkdir(path, 0755) < 0 && errno != EEXIST)
        dprintf(STDERR_FILENO, "ipad-linux: mkdir %s failed: %d\n", path, errno);
}

static void mount_fs(const char *source, const char *target, const char *type,
                     unsigned long flags, const char *data)
{
    make_dir(target);
    if (mount(source, target, type, flags, data) < 0)
        dprintf(STDERR_FILENO, "ipad-linux: mount %s on %s failed: %d\n",
                type, target, errno);
}

static void dump_file(const char *label, const char *path, size_t limit)
{
    char buffer[1024];
    int fd = open(path, O_RDONLY | O_CLOEXEC);

    dprintf(STDOUT_FILENO, "\n[%s] %s\n", label, path);

    if (fd < 0) {
        dprintf(STDOUT_FILENO, "<unavailable: errno=%d>\n", errno);
        return;
    }

    size_t total = 0;
    while (total < limit) {
        size_t want = sizeof(buffer);
        if (want > limit - total)
            want = limit - total;

        ssize_t got = read(fd, buffer, want);
        if (got <= 0)
            break;

        if (!write_all(STDOUT_FILENO, buffer, (size_t)got))
            break;
        total += (size_t)got;
    }

    if (total == limit)
        dprintf(STDOUT_FILENO, "\n<truncated at %zu bytes>\n", limit);
    else
        (void)write_all(STDOUT_FILENO, "\n", 1);

    close(fd);
}

static int read_text(const char *path, char *buffer, size_t size)
{
    if (!buffer || size < 2)
        return 0;

    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0)
        return 0;

    ssize_t got = read(fd, buffer, size - 1);
    close(fd);
    if (got <= 0)
        return 0;

    buffer[got] = '\0';
    while (got > 0 && (buffer[got - 1] == '\n' || buffer[got - 1] == '\r'))
        buffer[--got] = '\0';
    return 1;
}

static int starts_with(const char *text, const char *prefix)
{
    while (*prefix) {
        if (*text++ != *prefix++)
            return 0;
    }
    return 1;
}

static int decimal_suffix(const char *text)
{
    if (!*text)
        return 0;

    while (*text) {
        if (*text < '0' || *text > '9')
            return 0;
        ++text;
    }
    return 1;
}

static unsigned list_dir(const char *label, const char *path,
                         const char *prefix, int require_decimal_suffix)
{
    DIR *dir = opendir(path);
    unsigned count = 0;

    dprintf(STDOUT_FILENO, "\n[%s] %s\n", label, path);

    if (!dir) {
        dprintf(STDOUT_FILENO, "<unavailable: errno=%d>\n", errno);
        return 0;
    }

    struct dirent *entry;
    while ((entry = readdir(dir)) != NULL) {
        const char *name = entry->d_name;

        if (name[0] == '.')
            continue;
        if (prefix && !starts_with(name, prefix))
            continue;
        if (require_decimal_suffix &&
            !decimal_suffix(name + strlen(prefix)))
            continue;

        dprintf(STDOUT_FILENO, "  %s\n", name);
        ++count;
    }

    closedir(dir);
    dprintf(STDOUT_FILENO, "count=%u\n", count);
    return count;
}

static unsigned dump_pci_devices(int *wifi4387, int *bt4387)
{
    const char *root = "/sys/bus/pci/devices";
    DIR *dir = opendir(root);
    unsigned count = 0;

    *wifi4387 = 0;
    *bt4387 = 0;
    dprintf(STDOUT_FILENO, "\n[PCI devices] %s\n", root);

    if (!dir) {
        dprintf(STDOUT_FILENO, "<unavailable: errno=%d>\n", errno);
        return 0;
    }

    struct dirent *entry;
    while ((entry = readdir(dir)) != NULL) {
        if (entry->d_name[0] == '.')
            continue;

        char path[512];
        char vendor[32] = "?";
        char device[32] = "?";
        char class_id[32] = "?";
        char driver[256] = "-";

        snprintf(path, sizeof(path), "%s/%s/vendor", root, entry->d_name);
        read_text(path, vendor, sizeof(vendor));
        snprintf(path, sizeof(path), "%s/%s/device", root, entry->d_name);
        read_text(path, device, sizeof(device));
        snprintf(path, sizeof(path), "%s/%s/class", root, entry->d_name);
        read_text(path, class_id, sizeof(class_id));
        snprintf(path, sizeof(path), "%s/%s/driver", root, entry->d_name);
        ssize_t n = readlink(path, driver, sizeof(driver) - 1);
        if (n > 0) {
            driver[n] = '\0';
            const char *slash = strrchr(driver, '/');
            if (slash)
                memmove(driver, slash + 1, strlen(slash + 1) + 1);
        }

        dprintf(STDOUT_FILENO, "  %s vendor=%s device=%s class=%s driver=%s\n",
                entry->d_name, vendor, device, class_id, driver);

        if (!strcmp(vendor, "0x14e4") && !strcmp(device, "0x4433"))
            *wifi4387 = 1;
        if (!strcmp(vendor, "0x14e4") && !strcmp(device, "0x5f71"))
            *bt4387 = 1;
        ++count;
    }

    closedir(dir);
    dprintf(STDOUT_FILENO, "count=%u\n", count);
    return count;
}

static void print_uname(void)
{
    struct utsname u;

    dprintf(STDOUT_FILENO, "\n[uname]\n");
    if (uname(&u) < 0) {
        dprintf(STDOUT_FILENO, "<uname failed: errno=%d>\n", errno);
        return;
    }

    dprintf(STDOUT_FILENO, "  sysname=%s\n", u.sysname);
    dprintf(STDOUT_FILENO, "  release=%s\n", u.release);
    dprintf(STDOUT_FILENO, "  machine=%s\n", u.machine);
}

int main(void)
{
    static const char banner[] =
        "\n"
        "============================================================\n"
        "ipad-linux early userspace\n"
        "target: iPad Air 5 Wi-Fi / J407 / T8103\n"
        "If you can read this on ttySAC0, Linux reached PID 1.\n"
        "============================================================\n";

    if (!write_all(STDOUT_FILENO, banner, sizeof(banner) - 1))
        return 1;

    mount_fs("devtmpfs", "/dev", "devtmpfs", 0, "mode=0755");
    mount_fs("proc", "/proc", "proc", 0, 0);
    mount_fs("sysfs", "/sys", "sysfs", 0, 0);

    print_uname();
    dump_file("cmdline", "/proc/cmdline", 1024);
    dump_file("device-tree model", "/sys/firmware/devicetree/base/model", 512);
    dump_file("memory", "/proc/meminfo", 2048);
    dump_file("interrupts", "/proc/interrupts", 8192);

    unsigned cpus = list_dir("online CPU nodes", "/sys/devices/system/cpu",
                             "cpu", 1);
    unsigned blocks = list_dir("block devices", "/sys/block", 0, 0);
    unsigned nvme = list_dir("NVMe class", "/sys/class/nvme", 0, 0);
    unsigned graphics = list_dir("graphics class", "/sys/class/graphics", 0, 0);
    unsigned usb = list_dir("USB device nodes", "/sys/bus/usb/devices", 0, 0);
    unsigned typec = list_dir("Type-C class", "/sys/class/typec", 0, 0);
    unsigned net = list_dir("network interfaces", "/sys/class/net", 0, 0);
    unsigned wlan = list_dir("wireless-like interfaces", "/sys/class/net", "wlan", 0);
    unsigned bluetooth = list_dir("Bluetooth class", "/sys/class/bluetooth", 0, 0);
    unsigned input = list_dir("input class", "/sys/class/input", 0, 0);
    unsigned sound = list_dir("sound class", "/sys/class/sound", 0, 0);

    int wifi4387 = 0;
    int bt4387 = 0;
    unsigned pci = dump_pci_devices(&wifi4387, &bt4387);

    dprintf(STDOUT_FILENO,
            "\n[summary]\n"
            "  cpu_nodes=%u (expected 8 for full J407 SMP)\n"
            "  block_devices=%u\n"
            "  nvme_controllers=%u\n"
            "  graphics_entries=%u\n"
            "  usb_entries=%u\n"
            "  typec_entries=%u\n"
            "  pci_functions=%u\n"
            "  net_interfaces=%u\n"
            "  wlan_interfaces=%u\n"
            "  bluetooth_entries=%u\n"
            "  input_entries=%u\n"
            "  sound_entries=%u\n",
            cpus, blocks, nvme, graphics, usb, typec, pci,
            net, wlan, bluetooth, input, sound);

    dprintf(STDOUT_FILENO, "  SMP=%s\n", cpus == 8 ? "PASS" : "INCOMPLETE");
    dprintf(STDOUT_FILENO, "  ANS2/NVMe=%s\n", nvme ? "DETECTED" : "NOT_DETECTED");
    dprintf(STDOUT_FILENO, "  USB=%s\n", usb ? "ENUMERATED" : "NOT_ENUMERATED");
    dprintf(STDOUT_FILENO, "  TYPEC=%s\n", typec ? "REGISTERED" : "NOT_REGISTERED");
    dprintf(STDOUT_FILENO, "  BCM4387-WIFI=%s\n", wifi4387 ? "DETECTED" : "NOT_DETECTED");
    dprintf(STDOUT_FILENO, "  BCM4387-BT=%s\n", bt4387 ? "DETECTED" : "NOT_DETECTED");
    dprintf(STDOUT_FILENO, "  WLAN-INTERFACE=%s\n", wlan ? "PRESENT" : "ABSENT");
    dprintf(STDOUT_FILENO, "  BLUETOOTH-CLASS=%s\n", bluetooth ? "PRESENT" : "ABSENT");
    dprintf(STDOUT_FILENO, "  INPUT=%s\n", input ? "ENUMERATED" : "NOT_ENUMERATED");
    dprintf(STDOUT_FILENO, "  SOUND=%s\n", sound ? "ENUMERATED" : "NOT_ENUMERATED");
    dprintf(STDOUT_FILENO, "  framebuffer/DRM=%s\n",
            graphics ? "ENUMERATED" : "NOT_ENUMERATED");

    dprintf(STDOUT_FILENO,
            "\nipad-linux: FIRST_BOOT_DIAGNOSTICS_COMPLETE\n"
            "ipad-linux: holding PID 1 for post-boot inspection\n");

    for (;;)
        pause();
}
