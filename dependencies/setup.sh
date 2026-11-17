#!/usr/bin/env bash
# FUTURE EXECUTION ONLY. Packaging-host dependency preparation; no compiler,
# CMake, Ninja, invalidation, configure, build, BTX or Atlas invocation.
set -euo pipefail
umask 022
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
: "${1:?usage: setup.sh RECORDS_DIR [CONTROL_RECEIPT_DIR]}"
mkdir -p -- "$1" "${2:-$here}"
records=$(cd -- "$1" && pwd -P)
control=$(cd -- "${2:-$here}" && pwd -P)
# Never leave a previous success receipt after a failed dependency attempt.
rm -f -- "$control/receipt.json" "$control/dependency-env.sh"
exec > >(tee "$records/dependencies-setup.log") 2>&1
. /etc/os-release
test "$ID" = ubuntu && test "$VERSION_ID" = 22.04
test "$(uname -m)" = x86_64 && test "$(dpkg --print-architecture)" = amd64
test "$(id -u)" = 0
getconf GNU_LIBC_VERSION | tee "$records/glibc.log"
test "$(getconf GNU_LIBC_VERSION)" = 'glibc 2.35'
export DEBIAN_FRONTEND=noninteractive
export LC_ALL=C.UTF-8
apt-get -o Acquire::Retries=2 update
# These direct dependencies retain the original apt closure for comparison. Rust and
# GTK/WebKit are unnecessary because this stage does not build or run Atlas.
# Pin required GCC/Qt identities; do not pin unrelated base/security packages.
gcc_version=11.4.0-1ubuntu1~22.04.3
qt_base_version=6.2.4+dfsg-2ubuntu1.1
apt-get install -y --no-install-recommends \
  ca-certificates curl git build-essential pkg-config python3 perl \
  "gcc-11=$gcc_version" "g++-11=$gcc_version" "cpp-11=$gcc_version" \
  "gcc-11-base=$gcc_version" "libgcc-11-dev=$gcc_version" "libstdc++-11-dev=$gcc_version" \
  libboost-dev libevent-dev libsqlite3-dev libzmq3-dev libqrencode-dev libgl-dev \
  "qt6-base-dev=$qt_base_version" "qt6-base-dev-tools=$qt_base_version" \
  'qt6-tools-dev=6.2.4-1' 'qt6-tools-dev-tools=6.2.4-1' 'qt6-l10n-tools=6.2.4-1' \
  librsvg2-bin imagemagick patchelf binutils
# Qt6Gui's WrapOpenGL discovery needs GL/gl.h even when the retained runtime
# libraries and libopengl-dev/libglx-dev are already installed. Fail here,
# before Python setup or project configure, if that explicit input is absent.
opengl_header=/usr/include/GL/gl.h
opengl_package=libgl-dev:amd64
test -f "$opengl_header"
test "$(dpkg-query -W -f='${db:Status-Abbrev}' "$opengl_package")" = 'ii '
dpkg-query -S "$opengl_header" | tee "$records/opengl-header-owner.log"
test "$(cat "$records/opengl-header-owner.log")" = "$opengl_package: $opengl_header"
dpkg-query -W -f='${binary:Package}\t${Version}\n' "$opengl_package" \
  > "$records/opengl-package.log"
sha256sum "$opengl_header" > "$records/opengl-header-sha256.log"
# Capture complete observed apt closure. This is evidence, not a reproducible
# lock or permission to trust old C++ objects without original header hashes.
dpkg-query -W -f='${binary:Package}\t${Version}\n' | sort > "$records/installed-packages.log"
apt-cache policy gcc-11 g++-11 qt6-base-dev qt6-base-dev-tools \
  qt6-tools-dev qt6-tools-dev-tools qt6-l10n-tools libgl-dev > "$records/required-apt-policy.log"
for package in gcc-11 g++-11 cpp-11 gcc-11-base libgcc-11-dev libstdc++-11-dev; do
  test "$(dpkg-query -W -f='${Version}' "$package")" = "$gcc_version"
done
for package in qt6-base-dev qt6-base-dev-tools; do
  test "$(dpkg-query -W -f='${Version}' "$package")" = "$qt_base_version"
done
for package in qt6-tools-dev qt6-tools-dev-tools qt6-l10n-tools; do
  test "$(dpkg-query -W -f='${Version}' "$package")" = 6.2.4-1
done
test "$(/usr/bin/qmake6 -query QT_VERSION)" = 6.2.4
/usr/bin/qmake6 -query > "$records/qt.log"
qtpaths=
for candidate in /usr/bin/qtpaths6 /usr/lib/qt6/bin/qtpaths6 /usr/lib/qt6/bin/qtpaths; do
  if test -x "$candidate"; then qtpaths=$candidate; break; fi
done
test -n "$qtpaths"
"$qtpaths" --qt-version | tee "$records/qtpaths.log"
test "$("$qtpaths" --qt-version)" = 6.2.4
for program in rsvg-convert convert; do command -v "$program"; done
pkg-config --modversion libevent sqlite3 libzmq libqrencode \
  > "$records/pkg-config-versions.log"
# Preserve original Qt development-file presence evidence without invoking
# a project generator or performing discovery through CMake.
for component in Qt6 Qt6Core Qt6Widgets; do
  test -f "/usr/lib/x86_64-linux-gnu/cmake/$component/${component}Config.cmake"
done
# The digest is from the reviewed production plan and original immutable setup.
# Install only into a fresh isolated container; never overwrite a shared prefix.
python_prefix=/opt/hostedtoolcache/Python/3.12.16/x64
test ! -e "$python_prefix"
python_setup=$(mktemp -d)
trap 'rm -rf -- "$python_setup"' EXIT
curl -fsSL --retry 2 --max-time 150 \
  https://github.com/actions/python-versions/releases/download/3.12.16-40260402378/python-3.12.16-linux-22.04-x64.tar.gz \
  -o "$python_setup/ubuntu-python.tar.gz"
printf '%s  %s\n' ebdd874c6bb02d1ade9069da60b6b09f8346ba0ae0db11e60e6ce90cf5542fb7 \
  "$python_setup/ubuntu-python.tar.gz" | sha256sum --check | tee "$records/python-archive-check.log"
mkdir "$python_setup/unpacked"
tar -xzf "$python_setup/ubuntu-python.tar.gz" -C "$python_setup/unpacked"
(cd "$python_setup/unpacked" && RUNNER_TOOL_CACHE=/opt/hostedtoolcache bash setup.sh)
python=$python_prefix/bin/python3
"$python" -VV | tee "$records/python-version.log"
# Direct wheels, all dependencies explicit, hashes mandatory, no indexes or
# source distributions; no implicit source build or dependency resolution.
PIP_CONFIG_FILE=/dev/null "$python" -I -m pip --isolated install \
  --disable-pip-version-check --no-cache-dir --no-index --no-deps \
  --only-binary=:all: --require-hashes -r "$here/wheels.lock"
PIP_CONFIG_FILE=/dev/null "$python" -I -m pip --isolated check
"$python" -I -m pip --isolated freeze --all > "$records/python-packages.log"
# Tool wheels remain installed to preserve the exact Python input closure.
# No compiler, CMake or Ninja executable is invoked or linked into command paths.
"$python" -I - "$here" "$records" "$control" "$qtpaths" <<'PY'
import cryptography, cffi, pycparser, hashlib, importlib.metadata, json, os
import pathlib, platform, sqlite3, subprocess, sys, sysconfig
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
here, records, control = map(pathlib.Path, sys.argv[1:4]); qtpaths = sys.argv[4]
assert sys.version_info[:3] == (3, 12, 16)
assert platform.machine() == 'x86_64'
expected = {'cmake':'3.31.6','ninja':'1.11.1.4','cryptography':'46.0.4','cffi':'2.0.0','pycparser':'2.23'}
for name, version in expected.items(): assert importlib.metadata.version(name) == version
include = pathlib.Path(sysconfig.get_path('include'))
header = include / 'Python.h'; config_header = pathlib.Path(sysconfig.get_config_h_filename())
library = pathlib.Path(sysconfig.get_config_var('LIBDIR')) / sysconfig.get_config_var('LDLIBRARY')
assert header.is_file() and config_header.is_file() and library.is_file()
assert sysconfig.get_config_var('Py_ENABLE_SHARED') == 1
assert '.so' in library.name
# Resolve the shared-library closure without compiling/linking any source.
linked = subprocess.run(['/usr/bin/ldd', str(library)], text=True, capture_output=True, check=True)
assert 'not found' not in linked.stdout
(records / 'python-shared-ldd.log').write_text(linked.stdout + linked.stderr)
elf = subprocess.run(['/usr/bin/readelf','-h',str(library)],text=True,capture_output=True,check=True)
assert 'Advanced Micro Devices X86-64' in elf.stdout
(records / 'python-shared-elf.log').write_text(elf.stdout)
opengl_header = pathlib.Path('/usr/include/GL/gl.h')
assert opengl_header.is_file()
opengl_package, opengl_version = (records / 'opengl-package.log').read_text().strip().split('\t')
assert opengl_package == 'libgl-dev:amd64'
assert (records / 'opengl-header-owner.log').read_text().strip() == f'{opengl_package}: {opengl_header}'
environment = {'BUILDER_PYTHON':str(pathlib.Path(sys.executable)),
 'Python3_ROOT_DIR':sys.prefix, 'Python3_EXECUTABLE':sys.executable}
receipt = {'schema':2,'status':'READY','scope':'package-only','python':sys.executable,
 'tools':{'qtpaths':qtpaths},
 'environment':environment,'python_development':{'include':str(include),'header':str(header),
 'config_header':str(config_header),'library':str(library),'shared':True,'elf_amd64':True,'ldd_resolved':True,
 'sha256':{str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in (header,config_header,library)}},
 'pip_bootstrap':{'observed_version':importlib.metadata.version('pip'),
 'policy':'Bundled archive installer upgrades pip from the network before wheels.lock; bootstrap is not hash locked.'},
 'opengl_development':{'header':str(opengl_header),'package':opengl_package,'version':opengl_version,
 'owner_verified':True,'header_sha256':hashlib.sha256(opengl_header.read_bytes()).hexdigest()},
 'imports':{'cryptography':cryptography.__version__,'cffi':cffi.__version__,'pycparser':pycparser.__version__,
 'sqlite3':sqlite3.sqlite_version,'AESGCM':AESGCM.__name__},
 'historical_compiler_probe_not_repeated':True,
 'objects_invalidated':False,'rebuild':False,'cpp_rebuild':False,'build_tool_invocations':0,
 'apt_reproducibility_claim':False,
 'inputs':{name:hashlib.sha256((here/name).read_bytes()).hexdigest() for name in ('wheels.lock','input-manifest.json','setup.sh')},
 'installed_packages_sha256':hashlib.sha256((records/'installed-packages.log').read_bytes()).hexdigest(),
 'records':str(records)}
# Shell values are explicitly quoted because this file is sourced by controller.
import shlex
(control / 'dependency-env.sh').write_text(''.join(f'export {key}={shlex.quote(value)}\n' for key,value in environment.items()))
tmp = control / 'receipt.json.tmp'; tmp.write_text(json.dumps(receipt,indent=2)+'\n'); tmp.replace(control / 'receipt.json')
(records / 'dependencies-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
PY
