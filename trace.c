/* Test-only wrapper around the frozen package bootstrap. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

typedef int (*run_string)(const char *, void *);

int PyRun_SimpleStringFlags(const char *code, void *flags)
{
    run_string original = (run_string)dlsym(RTLD_NEXT, "PyRun_SimpleStringFlags");
    if (!original) return -1;
    int result = original(code, flags);
    if (result == 0 && strstr(code, "class _SwapNetFrozenImporter(")) {
        result = original("exec(compile(open('trace.py', 'rb').read(), 'trace.py', 'exec'))", flags);
    }
    return result;
}
