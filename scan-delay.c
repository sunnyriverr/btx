/* Test-only delay for an actual read of an owned regtest block file. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <fcntl.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

size_t fread(void *buf, size_t size, size_t count, FILE *stream)
{
    size_t (*read_real)(void *, size_t, size_t, FILE *) = dlsym(RTLD_NEXT, "fread");
    const char *gate = getenv("BTX_RECOVERY_DELAY_GATE");
    const char *observed = getenv("BTX_RECOVERY_DELAY_OBSERVED");
    if (gate && observed && access(gate, F_OK) == 0) {
        char fd_path[64], path[PATH_MAX];
        snprintf(fd_path, sizeof(fd_path), "/proc/self/fd/%d", fileno(stream));
        ssize_t n = readlink(fd_path, path, sizeof(path) - 1);
        if (n >= 0) {
            path[n] = '\0';
            if (strstr(path, "/regtest/blocks/blk")) {
                int marker = open(observed, O_WRONLY | O_CREAT | O_CLOEXEC, 0600);
                if (marker >= 0) close(marker);
                for (int i = 0; i < 120 && access(gate, F_OK) == 0; ++i) usleep(100000);
            }
        }
    }
    return read_real(buf, size, count, stream);
}
