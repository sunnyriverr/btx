#!/usr/bin/env python3
"""Mac component linkage checks; strong-mode wrappers are NOT Windows builds."""
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
BUILD = ROOT / 'build'
BUILD.mkdir(exist_ok=True)
MIN_FREE = 1342177280
RESULTS = []
CLANG = '/usr/bin/clang++'

def run(label, command):
    if shutil.disk_usage(ROOT).free < MIN_FREE + 10_000_000:
        raise RuntimeError('Insufficient disk reserve')
    p = subprocess.run(command, text=True, capture_output=True, timeout=60)
    log = BUILD / (label + '.log')
    log.write_text(p.stdout + p.stderr)
    row = {'label': label, 'command': list(map(str, command)), 'exit': p.returncode,
           'log': str(log.relative_to(ROOT)), 'free_after': shutil.disk_usage(ROOT).free}
    RESULTS.append(row)
    (ROOT / 'results.json').write_text(json.dumps(RESULTS, indent=2) + '\n')
    return p

def ok(label, command):
    p = run(label, command)
    if p.returncode:
        raise RuntimeError(label + ': ' + p.stderr[-1800:])
    return p

def compile_file(label, path, include, flags=()):
    obj = BUILD / (label + '.o')
    ok(label, [CLANG, '-std=c++20', '-O0', '-I' + str(include), *flags,
               '-c', str(path), '-o', str(obj)])
    return obj

DRIVER = r'''
#include <matmul/accel_v4.h>
#include <primitives/block.h>
#include <cuda/matmul_v4_bmx4_accel.h>
#include <metal/matmul_v4_accel.h>
#include <metal/matmul_v4_bmx4_accel.h>
#include <hip/matmul_v4_accel.h>
#include <hip/matmul_v4_bmx4_accel.h>
#include <cstdio>
#ifndef TEST_CUDA
#define TEST_CUDA 0
#endif
#ifndef TEST_METAL
#define TEST_METAL 0
#endif
#ifndef TEST_HIP
#define TEST_HIP 0
#endif
#define CHECK(x) do { if (!(x)) { std::fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x); return 1; } } while (0)
#define CHECK_VENDOR(ns, enabled, clears) do { \
    digest.begin()[0] = 17; payload = {23}; \
    CHECK(matmul_v4::ns::ComputeDigestAccel(h, 1, 1, digest, payload) == bool(enabled)); \
    CHECK(digest.begin()[0] == 17); CHECK(payload == std::vector<unsigned char>({enabled ? 42u : 23u})); \
    digests = {digest}; payloads = {{23}}; \
    CHECK(matmul_v4::ns::ComputeDigestsBatchedAccel(headers, 1, 1, digests, payloads) == bool(enabled)); \
    CHECK(digests.size() == (clears ? 0u : 1u)); \
    CHECK(payloads == (clears ? std::vector<std::vector<unsigned char>>{} : std::vector<std::vector<unsigned char>>{{enabled ? 42u : 23u}})); \
    digests = {digest}; payloads = {{23}}; \
    CHECK(matmul_v4::ns::ComputeDigestsBMX4CAccel(headers, 1, 1, digests, payloads) == bool(enabled)); \
    CHECK(digests.size() == (clears ? 0u : 1u)); \
    CHECK(payloads == (clears ? std::vector<std::vector<unsigned char>>{} : std::vector<std::vector<unsigned char>>{{enabled ? 42u : 23u}})); \
} while (0)
int main() {
    CBlockHeader h;
    std::vector<CBlockHeader> headers{h};
    uint256 digest;
    std::vector<unsigned char> payload;
    std::vector<uint256> digests;
    std::vector<std::vector<unsigned char>> payloads;
    CHECK_VENDOR(cuda, TEST_CUDA, false);
    CHECK_VENDOR(metal, TEST_METAL, false);
    CHECK_VENDOR(hip, TEST_HIP, !TEST_HIP);
    CHECK_VENDOR(ascend, false, false);
#if !TEST_CUDA
    std::vector<matmul::v4::bmx4::DigestOnlyResultBMX4C> results;
    CHECK(!matmul_v4::cuda::ComputeDigestsOnlyBMX4CAccel(headers, 1, 1, digest, results, &payloads));
#endif
#if !TEST_METAL
    CHECK(!matmul_v4::metal::ProbeAcceleration().available);
    CHECK(!matmul_v4::bmx4::metal::ProbeAcceleration().available);
#endif
#if !TEST_HIP
    CHECK(!matmul_v4::hip::HipBackendCompiled());
    CHECK(!matmul_v4::bmx4::hip::Bmx4CHipBackendCompiled());
    digests = {digest}; payloads = {{23}};
    CHECK(!matmul_v4::bmx4::hip::ComputeDigestsBMX4CAccel(headers, 1, 1, digests, payloads));
    CHECK(digests.empty() && payloads.empty());
#endif
    std::puts("PASS: all 12 dispatcher entry points, outputs and selected vendor surfaces");
}
'''

def provider(vendor):
    return '''#include <matmul/accel_v4.h>
namespace matmul_v4::VENDOR {
bool ComputeDigestAccel(const CBlockHeader&, uint32_t, uint32_t, uint256&, std::vector<unsigned char>& p) { p = {42}; return true; }
bool ComputeDigestsBatchedAccel(const std::vector<CBlockHeader>&, uint32_t, uint32_t, std::vector<uint256>&, std::vector<std::vector<unsigned char>>& p) { p = {{42}}; return true; }
bool ComputeDigestsBMX4CAccel(const std::vector<CBlockHeader>&, uint32_t, uint32_t, std::vector<uint256>&, std::vector<std::vector<unsigned char>>& p) { p = {{42}}; return true; }
}
'''.replace('VENDOR', vendor)

def generic(variant, mode, flags=()):
    include = ROOT / variant / 'src'
    source = include / 'matmul/accel_v4_stub.cpp'
    label = variant + '-' + mode + ('-' + '-'.join(flags).replace('=', '_') if flags else '')
    wrapper = BUILD / (label + '.cpp')
    # Parse real project/stdlib headers natively first. Only then exercise the
    # generic TU's exact platform linkage branch. This is host emulation only.
    macro = {'native': '', 'msvc': '#define _MSC_VER 1944\n', 'mingw': '#define __MINGW32__ 1\n'}[mode]
    wrapper.write_text('#include <matmul/accel_v4.h>\n#include <cstdint>\n#include <vector>\n' + macro + '#include "' + str(source) + '"\n')
    obj = compile_file(label, wrapper, include, flags)
    symbols = ok(label + '-symbols', ['/usr/bin/nm', '-g', '-U', str(obj)]).stdout
    count = sum(' T ' in s or ' W ' in s for s in symbols.splitlines())
    expected = 12 if variant == 'source' and not flags else 3
    if variant == 'source' and flags:
        expected = 9
    if count != expected:
        raise RuntimeError(f'{label}: expected {expected} defined functions, got {count}')
    details = ok(label + '-symbol-strength', ['/usr/bin/nm', '-m', '-g', '-U', str(obj)]).stdout
    if mode != 'native' and 'weak external' in details:
        raise RuntimeError(label + ': expected ordinary strong definitions')
    return obj

def link_run(label, objects, driver, expected_duplicate=False, archive=False, force=False):
    exe = BUILD / label
    if archive:
        lib = BUILD / (label + '.a')
        lib.unlink(missing_ok=True)
        ok(label + '-archive', ['/usr/bin/ar', 'rcs', str(lib), *map(str, objects)])
        inputs = ['-Wl,-force_load,' + str(lib)] if force else [str(lib)]
    else:
        inputs = list(map(str, objects))
    p = run(label + '-link', [CLANG, str(driver), *inputs, '-o', str(exe)])
    if expected_duplicate:
        if p.returncode == 0 or 'duplicate symbol' not in p.stderr:
            raise RuntimeError(label + ': expected duplicate-symbol failure')
        return
    if p.returncode:
        raise RuntimeError(label + ': ' + p.stderr[-1500:])
    ok(label + '-run', [str(exe)])

def main():
    # This is a source-ownership assertion, not a full CMake configure or SDK
    # build. It binds the handwritten component object list to the real graph.
    original_cmake = (ROOT / 'source/src/CMakeLists.txt').read_text()
    candidate_cmake = (ROOT / 'candidate/src/CMakeLists.txt').read_text()
    strip_comments = lambda s: '\n'.join(re.sub(r'#.*', '', line).strip() for line in s.splitlines() if re.sub(r'#.*', '', line).strip())
    if strip_comments(original_cmake) != strip_comments(candidate_cmake):
        raise RuntimeError('Candidate unexpectedly changes CMake commands')
    assert 'matmul/accel_v4_stub.cpp' in original_cmake
    for vendor, condition, suffix, next_condition in [
        ('metal', 'APPLE AND BTX_ENABLE_METAL', '.mm', 'BTX_ENABLE_CUDA_EXPERIMENTAL'),
        ('cuda', 'BTX_ENABLE_CUDA_EXPERIMENTAL', '.cu', 'BTX_ENABLE_HIP'),
        ('hip', 'BTX_ENABLE_HIP', '.hip', 'BTX_ENABLE_ASCEND AND BTX_HAVE_CANN'),
    ]:
        start = original_cmake.index('if(' + condition + ')', original_cmake.index('add_library(btx_matmul_backend'))
        stop = original_cmake.index('if(' + next_condition + ')', start + 1)
        block = original_cmake[start:stop]
        boundary = block.index('else()\n  target_sources(btx_matmul_backend PRIVATE\n    ' + vendor + '/')
        enabled, disabled = block[:boundary], block[boundary:]
        for stem in ('matmul_v4_accel', 'matmul_v4_bmx4_accel'):
            assert vendor + '/' + stem + suffix in enabled
            assert vendor + '/' + stem + '_stub.cpp' in disabled
            assert vendor + '/' + stem + '_stub.cpp' not in enabled
        if vendor == 'hip':
            assert 'add_library(btx_hip_device STATIC' in enabled
            assert 'target_link_libraries(btx_matmul_backend PRIVATE btx_hip_device)' in enabled
    (ROOT / 'build-graph-check.json').write_text(json.dumps({'status': 'PASS', 'scope': 'Exact CMake source assertions; no configure or GPU build'}, indent=2) + '\n')
    include = ROOT / 'source/src'
    driver_path = BUILD / 'driver.cpp'; driver_path.write_text(DRIVER)
    driver = compile_file('driver', driver_path, include)
    vendors = {}
    for vendor in ('cuda', 'metal', 'hip'):
        vendors[vendor] = [compile_file(vendor + suffix, include / vendor / ('matmul_v4' + suffix + '_stub.cpp'), include)
                           for suffix in ('_accel', '_bmx4_accel')]
    all_vendors = sum(vendors.values(), [])
    for mode in ('native', 'msvc', 'mingw'):
        for variant in ('source', 'candidate'):
            obj = generic(variant, mode)
            duplicate = variant == 'source' and mode != 'native'
            objects = [obj, *all_vendors]
            link_run(variant + '-' + mode + '-direct', objects, driver, duplicate)
            link_run(variant + '-' + mode + '-forced-archive', objects, driver, duplicate, True, True)
            if not duplicate:
                link_run(variant + '-' + mode + '-ordinary-archive', objects, driver, archive=True)
    # One enabled vendor at a time: real disabled stubs for the others, explicit
    # marker providers for enabled entries. No GPU or algorithm execution claim.
    for vendor, define in [('cuda', 'BTX_ENABLE_CUDA_EXPERIMENTAL'), ('metal', 'BTX_ENABLE_METAL'), ('hip', 'BTX_ENABLE_HIP')]:
        marker_path = BUILD / (vendor + '-provider.cpp'); marker_path.write_text(provider(vendor))
        marker = compile_file(vendor + '-provider', marker_path, include)
        d = compile_file(vendor + '-driver', driver_path, include, ['-DTEST_' + vendor.upper() + '=1'])
        for variant in ('source', 'candidate'):
            obj = generic(variant, 'msvc', ['-D' + define + '=1', '-DBTX_ENABLE_ASCEND=1', '-DBTX_HAVE_CANN=1'])
            other = sum([v for k, v in vendors.items() if k != vendor], [])
            # Baseline still duplicates the two disabled vendors. Candidate
            # must select all three marker functions and retain Ascend.
            link_run(variant + '-enabled-' + vendor, [obj, *other, marker], d, variant == 'source', True, True)
        if vendor == 'metal':
            exe = BUILD / 'wrong-provider-control'
            ok('wrong-provider-control-link', [CLANG, str(d), str(obj), *map(str, all_vendors), '-o', str(exe)])
            p = run('wrong-provider-control-run', [str(exe)])
            if p.returncode == 0 or 'FAIL line' not in p.stderr:
                raise RuntimeError('Oracle did not reject a disabled stub replacing the enabled provider')
    (ROOT / 'summary.json').write_text(json.dumps({'status': 'PASS', 'scope': 'macOS component; strong-branch emulation, not native Windows', 'harness_sha256': hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(), 'commands': len(RESULTS)}, indent=2) + '\n')
    print('PASS: component linkage, fallback behavior and enabled-provider controls; Windows remains unverified')

if __name__ == '__main__':
    main()
