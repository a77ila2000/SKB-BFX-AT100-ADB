#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/ioctl.h>
#include <unistd.h>

struct binder_version { int32_t protocol_version; };
_Static_assert(sizeof(struct binder_version) == 4, "Binder version ABI");

int main(void) {
    struct binder_version version = {0};
    int fd = open("/dev/binder", O_RDONLY | O_CLOEXEC);
    if (fd < 0) { perror("open binder"); return 1; }
    int status = ioctl(fd, _IOWR('b', 9, struct binder_version), &version);
    close(fd);
    if (status < 0) { perror("BINDER_VERSION"); return 1; }
    printf("{\"pointer_bits\":%zu,\"binder_protocol\":%d}\n",
           sizeof(void *) * 8, version.protocol_version);
    return version.protocol_version == 7 || version.protocol_version == 8 ? 0 : 2;
}
