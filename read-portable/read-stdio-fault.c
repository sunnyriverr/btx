// Test-only fault for a single disposable JSONL input.
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

struct fault_file {
    FILE* input;
    size_t offset;
};

static ssize_t fault_read_common(struct fault_file* stream, char* output, size_t size)
{
    const size_t prefix = 256;
    if (stream->offset == prefix && access(getenv("BTX_LABEL_READ_ARM"), F_OK) == 0) {
        const char msg[] = "BTX_LABEL_PROBE: target read returned EIO after prefix\n";
        (void)write(STDERR_FILENO, msg, sizeof(msg) - 1);
        errno = EIO;
        return -1;
    }
    if (stream->offset < prefix && size > prefix - stream->offset) size = prefix - stream->offset;
    size_t count = fread(output, 1, size, stream->input);
    if (ferror(stream->input)) return -1;
    stream->offset += count;
    return count;
}

#ifdef __APPLE__
static int fault_read(void* arg, char* output, int size) { return (int)fault_read_common(arg, output, size); }
#else
static ssize_t fault_read(void* arg, char* output, size_t size) { return fault_read_common(arg, output, size); }
#endif

static int fault_close(void* arg)
{
    struct fault_file* stream = arg;
    int rc = fclose(stream->input);
    free(stream);
    return rc;
}

static FILE* probe_open(const char* path, const char* mode)
{
#ifdef __APPLE__
    FILE* input = fopen(path, mode);
#else
    FILE* (*real_open)(const char*, const char*) = dlsym(RTLD_NEXT, "fopen");
    FILE* input = real_open(path, mode);
#endif
    const char* target = getenv("BTX_LABEL_READ_TARGET");
    const char* arm = getenv("BTX_LABEL_READ_ARM");
    if (!input || !target || !arm || strcmp(path, target) != 0 || access(arm, F_OK) != 0) return input;
    struct fault_file* stream = calloc(1, sizeof(*stream));
    if (!stream) { fclose(input); return NULL; }
    stream->input = input;
#ifdef __APPLE__
    FILE* hooked = funopen(stream, fault_read, NULL, NULL, fault_close);
#else
    FILE* hooked = fopencookie(stream, mode, (cookie_io_functions_t){.read = fault_read, .close = fault_close});
#endif
    if (!hooked) fault_close(stream);
    return hooked;
}

#ifdef __APPLE__
__attribute__((used, section("__DATA,__interpose")))
static const struct { const void* replacement; const void* original; } hook = {
    (const void*)probe_open, (const void*)fopen,
};
#else
FILE* fopen(const char* path, const char* mode) { return probe_open(path, mode); }
FILE* fopen64(const char* path, const char* mode) { return probe_open(path, mode); }
#endif
