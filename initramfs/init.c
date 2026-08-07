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

        write(STDOUT_FILENO, buffer, (size_t)got);
        total += (size_t)got;
    }

    if (total == limit)
        dprintf(STDOUT_FILENO, "\n<truncated at %zu bytes>\n", limit);
    else
        write(STDOUT_FILENO, "\n", 1);

    close(fd);
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

    write(STDOUT_FILENO, banner, sizeof(banner) - 1);

    mount_fs("devtmpfs", "/dev", "devtmpfs", 0, "mode=0755");
    mount_fs("proc", "/proc", "proc", 0, 0);
    mount_fs("sysfs", "/sys", "sysfs", 0, 0);

    print_uname();
    dump_file("cmdline", "/proc/cmdline", 1024);
    dump_file("memory", "/proc/meminfo", 2048);

    unsigned cpus = list_dir("online CPU nodes", "/sys/devices/system/cpu",
                             "cpu", 1);
    unsigned blocks = list_dir("block devices", "/sys/block", 0, 0);
    unsigned nvme = list_dir("NVMe class", "/sys/class/nvme", 0, 0);
    unsigned graphics = list_dir("graphics class", "/sys/class/graphics", 0, 0);

    dprintf(STDOUT_FILENO,
            "\n[summary]\n"
            "  cpu_nodes=%u (expected 8 for full J407 SMP)\n"
            "  block_devices=%u\n"
            "  nvme_controllers=%u\n"
            "  graphics_entries=%u\n",
            cpus, blocks, nvme, graphics);

    if (cpus == 8)
        dprintf(STDOUT_FILENO, "  SMP=PASS\n");
    else
        dprintf(STDOUT_FILENO, "  SMP=INCOMPLETE\n");

    if (nvme)
        dprintf(STDOUT_FILENO, "  ANS2/NVMe=DETECTED\n");
    else
        dprintf(STDOUT_FILENO, "  ANS2/NVMe=NOT_DETECTED\n");

    if (graphics)
        dprintf(STDOUT_FILENO, "  framebuffer/DRM=ENUMERATED\n");
    else
        dprintf(STDOUT_FILENO, "  framebuffer/DRM=NOT_ENUMERATED\n");

    dprintf(STDOUT_FILENO,
            "\nipad-linux: FIRST_BOOT_DIAGNOSTICS_COMPLETE\n"
            "ipad-linux: holding PID 1 for post-boot inspection\n");

    for (;;)
        pause();
}
