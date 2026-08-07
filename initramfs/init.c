#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/types.h>
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

int main(void)
{
    static const char banner[] =
        "\n"
        "ipad-linux early userspace\n"
        "target: iPad Air 5 Wi-Fi / J407 / T8103\n"
        "If you can read this on ttySAC0, the arm64 kernel reached PID 1.\n"
        "\n";

    write(STDOUT_FILENO, banner, sizeof(banner) - 1);

    mount_fs("devtmpfs", "/dev", "devtmpfs", 0, "mode=0755");
    mount_fs("proc", "/proc", "proc", 0, 0);
    mount_fs("sysfs", "/sys", "sysfs", 0, 0);

    dprintf(STDOUT_FILENO, "ipad-linux: /proc, /sys and /dev setup attempted\n");
    dprintf(STDOUT_FILENO, "ipad-linux: holding PID 1 for bring-up diagnostics\n");

    for (;;)
        pause();
}
