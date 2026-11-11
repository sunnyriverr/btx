"""Compare the real Linux loader and exact #477 gate with one compiled plugin."""
from hashlib import sha256
from pathlib import Path
import importlib.util
import os
import subprocess
import sys
import tempfile

def run(*args, **kw):
    return subprocess.run(args, text=True, capture_output=True, **kw)

def checked(*args, **kw):
    out = run(*args, **kw)
    if out.returncode:
        raise RuntimeError(f"{args}: {out.returncode}\n{out.stdout}\n{out.stderr}")
    return out.stdout.strip()

def load(path):
    spec = importlib.util.spec_from_file_location("pack", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

here = Path(__file__).resolve().parent
old, new = (load(here / name / "package_release_archive.py") for name in ("old", "new"))
clean_env = {k: v for k, v in os.environ.items() if not k.startswith("LD_")}
soname = "libbtx_fixture_477.so.1"
abi = "GLIBCXX_3.4.99"

print(checked("uname", "-sm"))
print(checked("gcc", "--version").splitlines()[0])
for variant in ("old", "new"):
    path = here / variant / "verify_release_btxd.py"
    print(variant, sha256(path.read_bytes()).hexdigest())
with tempfile.TemporaryDirectory(dir=here) as temp:
    tmp = Path(temp)
    stage = tmp / "archive"
    for d in ("plugins", "unrelated", "lib"):
        (stage / d).mkdir(parents=True)
    (tmp / "provider.c").write_text("int fixture_answer(void) { return 477; }\n")
    (tmp / "provider.map").write_text(abi + " { global: fixture_answer; local: *; };\n")
    (tmp / "plugin.c").write_text("extern int fixture_answer(void); int plugin_answer(void) { return fixture_answer(); }\n")
    (tmp / "driver.c").write_text("""
#ifdef BTX_GLIBC_DRIVER
extern void* dlopen(const char*, int);
extern void* dlsym(void*, const char*);
extern char* dlerror(void);
extern int dlclose(void*);
extern int puts(const char*);
extern int fprintf(void*, const char*, ...);
extern void* stderr;
#define RTLD_NOW 2
#define RTLD_LOCAL 0
#else
#include <dlfcn.h>
#include <stdio.h>
#endif
int main(int argc, char** argv) {
    if (argc != 2) return 90;
    void* p = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!p) { fprintf(stderr, "%s\\n", dlerror()); return 44; }
    int (*answer)(void) = (int (*)(void))dlsym(p, "plugin_answer");
    if (!answer || answer() != 477) return 45;
    puts("plugin returned 477");
    return dlclose(p) != 0;
}
""")
    provider = stage / "unrelated" / soname
    plugin = stage / "plugins/libplugin.so"
    checked("gcc", "-shared", "-fPIC", "-nostdlib", str(tmp / "provider.c"),
            f"-Wl,-soname,{soname}", f"-Wl,--version-script={tmp / 'provider.map'}", "-o", str(provider))
    checked("gcc", "-shared", "-fPIC", "-nostdlib", str(tmp / "plugin.c"), str(provider),
            "-Wl,-z,defs,--enable-new-dtags,-rpath,$ORIGIN/../lib", "-o", str(plugin))
    if len(sys.argv) > 1:
        libc = Path(sys.argv[1])
        loader = libc / "ld-linux-aarch64.so.1"
        print("glibc", checked(str(loader), "--version").splitlines()[0])
        (tmp / "start.S").write_text("""
.text
.global _start
_start:
    mov x6, sp
    ldr x1, [sp]
    add x2, sp, #8
    adrp x0, main
    add x0, x0, :lo12:main
    mov x3, xzr
    mov x4, xzr
    mov x5, xzr
    bl __libc_start_main
    brk #0
.section .note.GNU-stack,"",@progbits
""")
        checked("gcc", "-DBTX_GLIBC_DRIVER", "-nostdlib", str(tmp / "start.S"),
                str(tmp / "driver.c"), str(libc / "libc.so.6"), f"-Wl,-dynamic-linker,{loader}",
                f"-Wl,-rpath,{libc}", "-o", str(tmp / "driver"))
    else:
        checked("gcc", str(tmp / "driver.c"), "-ldl", "-o", str(tmp / "driver"))
    needs = checked("readelf", "-V", str(plugin))
    assert abi in needs and soname in needs, needs
    print(needs)
    print(checked("readelf", "-l", str(tmp / "driver")).split("Requesting program interpreter: ")[1].split("]")[0])
    print("plugin_sha256", sha256(plugin.read_bytes()).hexdigest())
    def gate(pack, expect_reject):
        try:
            pack.verify_staged_abi_floor(stage)
        except RuntimeError as exc:
            assert expect_reject and abi in str(exc) and soname in str(exc), str(exc)
            return "reject"
        assert not expect_reject, "gate accepted the broken package"
        return "accept"
    for reachable in (False, True):
        if reachable:
            provider.rename(stage / "lib" / soname)
        result = run(str(tmp / "driver"), str(plugin), env=clean_env)
        if reachable:
            assert result.returncode == 0 and result.stdout.strip() == "plugin returned 477", result
        else:
            assert result.returncode == 44 and soname in result.stderr, result
        print("reachable", reachable, "loader", result.returncode, (result.stderr or result.stdout).strip(),
              "old", gate(old, False), "new", gate(new, not reachable))
