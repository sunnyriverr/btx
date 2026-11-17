# Packaging-host dependency preparation — source only

This adapted recipe prepares a future fresh isolated Ubuntu 22.04 amd64
packaging host. It has not been executed, syntax checked, imported, installed,
configured or tested during this source-only preparation. Original setup and
its retained receipts remain immutable evidence.

Future invocation under separate execution authority:

```
bash control/dependencies/setup.sh package-records control/dependencies
```

Arguments remain the records directory and optional control receipt directory;
both resolve to absolute paths. Success emits a separate `receipt.json`,
`dependency-env.sh`, and `dependencies-receipt.json` in records. Failure removes
any previous success receipt from this new receipt directory. The controller
must never use the historical compiled-input receipt directory as this output.
The controller enforces timeout, capacity and retention limits.

The receipt contract is `schema: 2`, `status: READY`, `scope: package-only`,
`cpp_rebuild: false`, `build_tool_invocations: 0`,
`historical_compiler_probe_not_repeated: true`, `objects_invalidated: false`,
and `rebuild: false`. It retains `python`, complete `python_development`, complete
`opengl_development`, complete `imports`, `pip_bootstrap`,
`installed_packages_sha256`, `records`, and `tools.qtpaths` evidence. Current
`inputs` hashes cover `setup.sh`, `input-manifest.json`, and `wheels.lock`.
`environment` contains only `BUILDER_PYTHON`, `Python3_ROOT_DIR`, and
`Python3_EXECUTABLE`, and those are the only emitted environment exports.

After restoring and before packaging, the controller compares `python`, all
`python_development`, all `opengl_development`, all `imports`,
`installed_packages_sha256`, and `tools.qtpaths` exactly to the original
compiled-input receipt. The three environment values must match their original
values. It validates current setup/manifest/lock hashes and requires the wheel
lock to remain byte-identical to the original. A mismatch is a stop for an input
decision; this recipe does not authorize invalidation, reconfiguration or a
rebuild. Historical compiler probes, CMake/Ninja runtime probes and invalidation
flags remain attributable only to their original runs, never this continuation.

The apt package list and version pins, Python archive URL/hash/prefix and exact
five-wheel lock retain the original compiled-input closure. GCC/tool packages
and CMake/Ninja wheels remain installed to allow the complete installed-package
baseline comparison. No compiler, CMake or Ninja executable is invoked; no
CMake/Ninja command links are created. Apt package/version evidence and wheel
metadata checks do not claim fresh compiler or build-tool execution evidence.
The recipe still observes Qt/qmake/qtpaths identities and the packaging tools,
OpenGL header owner/version/hash, and Python headers/shared library with ELF
amd64 and resolved shared-library closure. These are packaging prerequisites.

GCC 11.4.0 package `11.4.0-1ubuntu1~22.04.3`, Qt base 6.2.4 package
`6.2.4+dfsg-2ubuntu1.1`, and Qt tools/l10n `6.2.4-1` remain pinned. The complete
observed installed-package log is hashed, and the controller requires exact
baseline equality. This does not claim apt bit reproducibility. No GTK/WebKit
runtime package is added here; the package helper records those later host
runtime additions separately while rejecting changes to preexisting packages.

The unchanged Python archive is digest-verified before its bundled installer
runs in a fresh prefix. The wheel installation retains direct URLs and hashes,
`--require-hashes`, `--only-binary=:all:`, `--no-deps`, `--no-index`, and isolated
pip. No application/tool source distribution or implicit source build is
selected. `cryptography`, `cffi`, `pycparser`, `sqlite3`, and `AESGCM` import and
Python shared-development evidence remain in the new receipt for exact
comparison. The archive installer still upgrades pip from the network before
the five locked wheels; its observed pip version and this bootstrap limitation
are recorded. The bootstrap has no new reproducibility claim.

The controller separately verifies immutable compiled-checkpoint restore,
source/profile/dependency identity and every original compiled binary digest.
It stages the exact selected `libpython3.12.so.1.0` into `qtbuild/lib` for the
existing input ELF loader path before the current packager's native version
probe. This is a packaging-host prerequisite and leaves current shipping ABI,
Python bundling and dependency gates intact. This recipe never patches ELF,
changes global loader configuration, invalidates objects, configures, compiles,
starts BTX/Atlas, runs a test, opens wallets or launches a GUI.
