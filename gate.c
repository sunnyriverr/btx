#define _GNU_SOURCE
#include <dlfcn.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static __thread FILE *watched;
static __thread unsigned reads;

static FILE *watch(FILE *f, const char *path, const char *mode)
{
    const char *expected = getenv("BTX_TEST_IDENTITY_LIST");
    const char *arm = getenv("BTX_TEST_ARM");
    if (f && expected && arm && mode[0] == 'r' && !strcmp(path, expected) &&
        !access(arm, F_OK) && ++reads == 2) watched = f;
    return f;
}

FILE *fopen(const char *path, const char *mode)
{
    FILE *(*next)(const char *, const char *) = dlsym(RTLD_NEXT, "fopen");
    return watch(next(path, mode), path, mode);
}

FILE *fopen64(const char *path, const char *mode)
{
    FILE *(*next)(const char *, const char *) = dlsym(RTLD_NEXT, "fopen64");
    return watch(next(path, mode), path, mode);
}

int fclose(FILE *f)
{
    int (*next)(FILE *) = dlsym(RTLD_NEXT, "fclose");
    const int stop = f == watched;
    if (stop) watched = NULL;
    const int result = next(f);
    if (stop) {
        const char *arrived = getenv("BTX_TEST_ARRIVED");
        const char *release = getenv("BTX_TEST_RELEASE");
        int fd = open(arrived, O_WRONLY | O_CREAT | O_EXCL, 0600);
        if (fd >= 0) {
            close(fd);
            for (unsigned i = 0; i < 500 && access(release, F_OK); ++i) usleep(10000);
        }
    }
    return result;
}
