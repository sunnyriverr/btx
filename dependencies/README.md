# Dependency preparation interface

Prepared as source only on 17 November 2026. This script has not been executed or tested. No wheels or Python archive were downloaded during preparation; only public PyPI JSON package metadata was read to select exact compatible binary-wheel URLs and hashes.

Future invocation, inside the separately authorized fresh Ubuntu 22.04 amd64 container as root:

```
bash control/dependencies/setup.sh preflight-records control/dependencies
```

Arguments are the records directory and optional control receipt directory; each is resolved to an absolute path. The receipt directory defaults to the script directory. On success the script writes `receipt.json`, `dependency-env.sh`, and a copy of the receipt in records. On failure it leaves no prior `READY` receipt. The controller must enforce its own timeout and retention margin.

The receipt includes `status: READY`, `python`, `tools` (`cmake`, `ninja`, `gxx`, `qtpaths`), exported `environment`, dependency input digests, complete observed installed-package receipt digest, Python headers/shared-library evidence, ELF amd64/shared-library closure checks and successful `cryptography`, `sqlite3`, `AESGCM`, `cffi`, `pycparser` imports. Header/library hashes are evidence of this run, not comparisons against the absent historical header baseline. The selected interpreter's import and sysconfig evidence does not replace current CMake's `Interpreter Development` discovery; the controller must require that discovery and pass this exact Python executable/root.

GCC 11.4.0 Ubuntu package `11.4.0-1ubuntu1~22.04.3`, Qt base 6.2.4 Ubuntu package `6.2.4+dfsg-2ubuntu1.1`, and Qt tools/l10n `6.2.4-1` are explicit requirements. All other apt versions are observed in the complete installed-package log, without failing the whole base for unrelated drift. This is not a bit-reproducibility claim. The controller **must invalidate all retained C++ objects** before reconfiguration: the historical package receipt supplies versions, not a full installed-header content baseline. `invalidate_all_old_cpp: true` makes this requirement machine readable. This script does not restore or invalidate any source/build output itself.

The five-wheel lock uses exact direct URLs, SHA256, `--require-hashes`, `--only-binary=:all:`, `--no-deps`, `--no-index` and isolated pip; installation cannot silently select an sdist or run a source build. CPython 3.12 satisfies cryptography's `cffi>=2.0.0` marker; cffi requires pycparser. No typing-extensions is needed on Python >=3.11. CMake's conditional importlib_metadata requirement applies only below Python 3.8. Wheels selected target x86_64 manylinux <=2.17 (and a pure Python pycparser wheel), compatible with glibc 2.35. Cryptography's cp311 abi3 wheel supports CPython 3.12. Metadata requires-dist and requires-python fields are retained in `input-manifest.json`; metadata hashes identify observations and are not downloaded wheel hashes.

The pinned Python archive is the original producer's Ubuntu 22.04 artifact and SHA256. Its bundled setup installer runs only after complete digest verification in the future isolated container and refuses an existing Python prefix. No retained producer `pilot.py`, BTX code, project generators, tests, project configure, builds, restoration, native BTX execution, Rust, Atlas build, GTK or WebKit is invoked. Current CMake configure belongs to the controller. Qt icon tool discovery retains librsvg `rsvg-convert` and ImageMagick `convert`; Boost, event, SQLite, ZMQ, QRencode and Qt development dependencies retain the current configure/Qt/ModelNet closure. Private OpenSSL is restored and validated by the controller, not this script.

The original mutable producer is read-only evidence and remains untouched. Exact original inputs: `producer/setup.sh`, production plan, published `cmake/SwapNet.cmake`, `CMakeLists.txt`, `src/qt/CMakeLists.txt` and run 43428864330's `CMakeCache.txt`, `gcc.log`, `qt.log`, `installed-packages.log`. Source review checked script scope, lock compatibility and closure; no shell syntax check, install, configure or runtime test was performed under source-only authority.
