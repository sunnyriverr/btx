#!/usr/bin/env python3
"""Native Windows before/after compile and FD-set regression; no node starts."""
import argparse, base64, hashlib, json, os, platform, shutil, subprocess, sys
from pathlib import Path

BASE = '107efc934847f57ecb16a6b1d204a94eed5d8df2'
CODE = '3ddffea282cd403da7e5d2350c8fd8990220eee5'
HERE = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    a = parser.parse_args()
    if sys.platform != 'win32' or platform.machine().lower() not in ('amd64', 'x86_64'):
        parser.error('Native x64 Windows required')
    if any(os.environ.get(k) for k in ('CL', '_CL_', 'LINK')):
        parser.error('Compiler override environment must be empty')
    out, repo = a.out.resolve(), a.repo.resolve()
    if out.exists() or not out.parent.is_dir():
        parser.error('New output directory required')
    tools = {k: shutil.which(k) for k in ('git', 'cmake', 'cl', 'clang-cl')}
    if not all(tools.values()):
        parser.error('Missing native tool')
    out.mkdir()
    def blob(rev, name):
        return subprocess.check_output([tools['git'], '-C', str(repo), 'show', rev+':'+name])
    manifest = json.loads((HERE/'closure.json').read_text())
    roots = {}
    source_ids = {}
    for variant, rev in [('before', BASE), ('after', CODE)]:
        root = out/variant
        roots[variant] = root
        source_ids[variant] = {}
        for name, expected in manifest['source_files'].items():
            data = blob(rev, name)
            digest = hashlib.sha256(data).hexdigest()
            if name not in ('src/compat/compat.h', 'src/compat/mingw/posix_extra.h'):
                assert digest == expected, name
            f = root/name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(data)
            source_ids[variant][name] = digest
        shim = (root/'src/compat/mingw/posix_extra.h').read_bytes()
        prefix, tail = shim.split(b'#include <csignal>', 1)
        assert prefix.count(b'#ifndef BTX_COMPAT_MINGW_POSIX_EXTRA_H') == 1
        # Explicit component boundary: exact cleanup prefix, not a complete shim.
        (root/'shim_cleanup_prefix.h').write_bytes(prefix+b'\n#endif\n#endif\n')
    regression = blob(CODE, 'test/util/windows_sdk_macro_tests.cpp')
    test = out/'regression.cpp'
    test.write_bytes(regression)
    prefix_test = out/'prefix-regression.cpp'
    body = regression.split(b'#include <type_traits>', 1)[1]
    prefix_test.write_bytes(b'#include "shim_cleanup_prefix.h"\n#include <type_traits>'+body)
    result = {'status': 'RUNNING', 'base': BASE, 'code': CODE, 'platform': platform.platform(),
              'python': sys.version, 'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'regression_sha256': hashlib.sha256(regression).hexdigest(), 'source_sha256': source_ids,
              'tools': tools, 'tool_sha256': {k: hashlib.sha256(Path(v).read_bytes()).hexdigest() for k,v in tools.items()},
              'sdk': {k: os.environ.get(k) for k in ('WindowsSDKVersion', 'VCToolsVersion', 'INCLUDE')},
              'profile': 'Explicit Windows component configuration, modelnet/wallet/GUI disabled; not a root CMake configure or node link.',
              'commands': []}
    def save():
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    def run(label, command, expected_ok=True):
        if shutil.disk_usage(out).free < 1342177280:
            raise RuntimeError('Disk reserve violated')
        command = list(map(str, command))
        q = subprocess.run(command, cwd=out, capture_output=True, text=True, errors='replace', timeout=120)
        (out/(label+'.log')).write_text(q.stdout+q.stderr, encoding='utf-8')
        row = {'label': label, 'command': command, 'exit': q.returncode,
               'expected_ok': expected_ok, 'matched': (q.returncode == 0) == expected_ok,
               'log': label+'.log'}
        result['commands'].append(row)
        save()
        return row
    try:
        # Use the real template, with all explicit component-profile substitutions recorded.
        variables = {'CLIENT_NAME': 'BTX', 'CLIENT_VERSION_MAJOR': '0', 'CLIENT_VERSION_MINOR': '35',
                     'CLIENT_VERSION_BUILD': '0', 'CLIENT_VERSION_IS_RELEASE': 'true', 'COPYRIGHT_YEAR': '2026',
                     'CLIENT_VERSION_STRING': '0.35.0rc1', 'COPYRIGHT_HOLDERS': 'The %s developers',
                     'COPYRIGHT_HOLDERS_FINAL': 'The BTX developers',
                     'CLIENT_BUGREPORT': 'https://github.com/btxchain/btx/issues',
                     'PROJECT_HOMEPAGE_URL': 'https://btx.dev/', 'HAVE_SYSTEM': '1', 'HAVE_WINDOWS_IOPRIO': '1'}
        result['config_variables'] = variables
        config = out/'generated'
        config.mkdir()
        cmake = out/'configure-component.cmake'
        script = '\n'.join('set('+k+' "'+v+'")' for k,v in variables.items())
        template = (roots['before']/'cmake/bitcoin-build-config.h.in').as_posix()
        script += '\nconfigure_file("'+template+'" "'+(config/'bitcoin-build-config.h').as_posix()+'" @ONLY)\n'
        cmake.write_text(script, encoding='utf-8')
        assert run('configure-component', [tools['cmake'], '-P', cmake])['matched']
        result['generated_config_sha256'] = hashlib.sha256((config/'bitcoin-build-config.h').read_bytes()).hexdigest()
        flags = ['/nologo', '/std:c++20', '/EHsc', '/Zc:__cplusplus', '/Zc:preprocessor', '/utf-8', '/sdl', '/MT', '/UNDEBUG',
                 '/DWIN32', '/D_WINDOWS', '/DWIN32_LEAN_AND_MEAN', '/DNOMINMAX', '/D_UNICODE', '/DUNICODE',
                 '/D_WIN32_WINNT=0x0A00', '/D_WIN32_IE=0x0A00',
                 '/D_CRT_SECURE_NO_WARNINGS', '/D_SILENCE_CXX17_CODECVT_HEADER_DEPRECATION_WARNING',
                 '/W3', '/wd4018', '/wd4146', '/wd4244', '/wd4267', '/wd4715', '/wd4805']
        for compiler in ('cl', 'clang-cl'):
            run(compiler+'-version', [tools[compiler], '--version'] if compiler == 'clang-cl' else [tools[compiler]])
            # cl with no source reports its version and usage; it is provenance, not a test case.
            result['commands'][-1]['expected_ok'] = None
            result['commands'][-1]['matched'] = True
            for variant, root in roots.items():
                inc = ['/I'+str(config), '/I'+str(root)]
                inc += ['/I'+str(root/x) for x in manifest['include_roots']]
                common = [tools[compiler], *flags, *inc]
                if compiler == 'clang-cl':
                    common.append('/clang:-ferror-limit=12')
                for order in ('late', 'sdk-first', 'shim-prefix'):
                    label = compiler+'-'+variant+'-'+order
                    exe = out/(label+'.exe')
                    src = prefix_test if order == 'shim-prefix' else test
                    cmd = [*common, src, '/Fo'+str(out/(label+'.obj')), '/Fe'+str(exe)]
                    if order == 'sdk-first':
                        cmd.append('/DBTX_SDK_FIRST')
                    cmd += ['/link', 'Ws2_32.lib']
                    row = run(label, cmd, variant == 'after')
                    if row['exit'] == 0:
                        run(label+'-run', [exe])
                for name in manifest['translation_units']:
                    label = compiler+'-'+variant+'-'+Path(name).stem
                    run(label, [*common, '/c', root/name, '/Fo'+str(out/(label+'.obj'))], variant == 'after')
        assert all(row['matched'] for row in result['commands']), 'Unexpected control/TU result; inspect logs'
        result['status'] = 'COLLECTED_PENDING_DIAGNOSTIC_REVIEW'
    except Exception as e:
        result['status'] = 'FAIL'
        result['error'] = repr(e)
        raise
    finally:
        save()
        for f in [out/'result.json', *sorted(out.glob('*.log'))]:
            encoded = base64.b64encode(f.read_bytes()).decode()
            print('BTX_FILE_BEGIN '+f.name)
            for i in range(0, len(encoded), 3000):
                print('BTX_FILE_DATA '+encoded[i:i+3000])
            print('BTX_FILE_END '+f.name)

if __name__ == '__main__':
    main()
