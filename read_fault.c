// Test-only fault for one disposable JSONL file in the child daemon.
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define PREFIX_BYTES 256

ssize_t read(int fd, void *buffer, size_t size)
{
    ssize_t (*real_read)(int, void *, size_t) = dlsym(RTLD_NEXT, "read");
    const char *target = getenv("BTX_LABEL_READ_TARGET");
    const char *armed = getenv("BTX_LABEL_READ_ARM");
    const int saved_errno = errno;
    if (size && target && armed && access(armed, F_OK) == 0) {
        char fd_path[64], path[PATH_MAX];
        snprintf(fd_path, sizeof(fd_path), "/proc/self/fd/%d", fd);
        const ssize_t len = readlink(fd_path, path, sizeof(path) - 1);
        if (len >= 0) {
            path[len] = '\0';
            if (strcmp(path, target) == 0) {
                const off_t offset = lseek(fd, 0, SEEK_CUR);
                if (offset >= PREFIX_BYTES) {
                    static const char msg[] = "BTX_LABEL_PROBE: target read returned EIO after prefix\n";
                    (void)write(STDERR_FILENO, msg, sizeof(msg) - 1);
                    errno = EIO;
                    return -1;
                }
                if (offset >= 0 && size > (size_t)(PREFIX_BYTES - offset)) {
                    size = PREFIX_BYTES - offset;
                }
            }
        }
    }
    errno = saved_errno;
    return real_read(fd, buffer, size);
}
