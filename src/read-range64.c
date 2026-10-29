#define _FILE_OFFSET_BITS 64
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <unistd.h>

_Static_assert(sizeof(off_t) == 8, "64-bit file offsets required");

static uint64_t number(const char *text) {
    char *end;
    errno = 0;
    if (*text < '0' || *text > '9') exit(2);
    unsigned long long value = strtoull(text, &end, 10);
    if (errno || *end || value > 16384) exit(2);
    return value;
}

int main(int argc, char **argv) {
    if (argc != 4) return 2;
    uint64_t offset = number(argv[2]) * UINT64_C(1048576);
    uint64_t remaining = number(argv[3]) * UINT64_C(1048576);
    if (!remaining || remaining > UINT64_C(268435456)) return 2;
    int fd = open(argv[1], O_RDONLY | O_CLOEXEC);
    if (fd < 0) { perror("open source read-only"); return 1; }
    struct stat st;
    if (fstat(fd, &st) || (!S_ISBLK(st.st_mode) && !S_ISREG(st.st_mode))) {
        fprintf(stderr, "Unsupported source type\n"); return 1;
    }
    unsigned char buffer[65536];
    while (remaining) {
        size_t wanted = remaining < sizeof(buffer) ? (size_t)remaining : sizeof(buffer);
        ssize_t count = pread(fd, buffer, wanted, (off_t)offset);
        if (count < 0 && errno == EINTR) continue;
        if (count <= 0) { perror("pread64 incomplete source"); return 1; }
        ssize_t written = 0;
        while (written < count) {
            ssize_t n = write(STDOUT_FILENO, buffer + written, (size_t)(count - written));
            if (n < 0 && errno == EINTR) continue;
            if (n <= 0) { perror("stdout write"); return 1; }
            written += n;
        }
        offset += (uint64_t)count;
        remaining -= (uint64_t)count;
    }
    if (close(fd)) { perror("close source"); return 1; }
    return 0;
}
