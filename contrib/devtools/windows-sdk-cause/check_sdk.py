#!/usr/bin/env python3
"""Bounded native SDK/header diagnosis; no product patch or dependency install."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

BASE = '107efc934847f57ecb16a6b1d204a94eed5d8df2'
RAW = '#define FD_SETSIZE 1024\n#include <winsock2.h>\n#include <ws2tcpip.h>\n#include <cstdint>\n'
CURRENT = '#include <compat/compat.h>\n'
SOCKET = '''void probe_socket() {
    fd_set recv;
    FD_ZERO(&recv);
    const SOCKET s = 0;
    FD_SET(s, &recv);
    (void)FD_ISSET(s, &recv);
}
'''
MESSAGES = '''#define BTX_STR_1(x) #x
#define BTX_STR(x) BTX_STR_1(x)
#pragma message("BTX_DIAG_FAR=" BTX_STR(FAR))
#pragma message("BTX_DIAG_NEAR=" BTX_STR(NEAR))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    a = parser.parse_args()
    if sys.platform != 'win32' or platform.machine().lower() not in ('amd64', 'x86_64'):
        parser.error('Native x64 Windows required')
    if any(os.environ.get(k) for k in ('CL', '_CL_', 'LINK')):
        parser.error('CL, _CL_ and LINK must be unset')
    repo, out = a.repo.resolve(), a.out.resolve()
    if out.exists() or not out.parent.is_dir():
        parser.error('Output must be new with existing parent')
    tools = {k: shutil.which(k) for k in ('git', 'clang-cl', 'cl')}
    if not all(tools.values()):
        parser.error('Missing required native compiler or git')
    out.mkdir()
    def blob(name):
        return subprocess.check_output([tools['git'], '-C', str(repo), 'show', BASE+':'+name])
    header = blob('src/compat/compat.h')
    assert b'#undef far' in header and b'#undef near' in header
    variants = {'current': header,
                'retain_far': header.replace(b'#undef far', b'// diagnostic: retain far'),
                'retain_near': header.replace(b'#undef near', b'// diagnostic: retain near'),
                'retain_both': header.replace(b'#undef far', b'// diagnostic: retain far').replace(b'#undef near', b'// diagnostic: retain near')}
    roots = {}
    for variant, data in variants.items():
        dest = out/variant/'src/compat/compat.h'
        dest.parent.mkdir(parents=True)
        dest.write_bytes(data)
        roots[variant] = dest.parent.parent
    roots['sdk'] = roots['current']
    evidence_names = ('src/compat/compat.h', 'src/util/sock.cpp', 'src/common/args.cpp',
                      'src/common/args.h', 'src/common/netif.cpp', 'src/common/netif.h',
                      'src/netaddress.h', 'CMakeLists.txt', 'CMakePresets.json')
    identities = {n: hashlib.sha256(blob(n)).hexdigest() for n in evidence_names}
    result = {'status': 'RUNNING', 'base': BASE, 'platform': platform.platform(),
              'python': sys.version, 'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'tools': tools, 'tool_sha256': {k: hashlib.sha256(Path(v).read_bytes()).hexdigest() for k,v in tools.items()},
              'source_sha256': identities, 'sdk': {k: os.environ.get(k) for k in
              ('WindowsSDKVersion', 'WindowsSdkDir', 'VCToolsVersion', 'INCLUDE')},
              'variant_header_sha256': {k: hashlib.sha256(v).hexdigest() for k,v in variants.items()},
              'cases': []}
    def save():
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    save()
    sdk = Path(os.environ['WindowsSdkDir'])/'Include'/os.environ['WindowsSDKVersion'].rstrip('\\/')
    snippets = {}
    for rel in ('shared/minwindef.h', 'um/winsock2.h'):
        f = sdk/rel
        data = f.read_bytes()
        text = data.decode('utf-8', errors='replace').splitlines()
        hits = []
        for i, line in enumerate(text):
            if re.match(r'^\s*#\s*define\s+(FAR|NEAR|far|near|FD_ZERO|FD_SET|FD_ISSET)\b', line):
                hits.append({'line': i+1, 'context': text[max(0,i-2):i+7]})
        snippets[rel] = {'sha256': hashlib.sha256(data).hexdigest(), 'snippets': hits}
    result['sdk_header_evidence'] = snippets
    # Retention variants are causal controls, not proposed product repairs.
    bodies = {'socket': SOCKET,
              'shell': '#include <shellapi.h>\n#include <shlobj.h>\n',
              'iphlpapi': '#include <iphlpapi.h>\n',
              'identifiers': 'int probe_identifiers() { int near = 1; int far = 2; return near + far; }\n'}
    cases = []
    for variant in ('sdk', 'current', 'retain_far', 'retain_near', 'retain_both'):
        for kind, body in bodies.items():
            expected = None
            if kind == 'socket':
                expected = variant in ('sdk', 'retain_far', 'retain_both')
            elif kind == 'identifiers':
                expected = variant == 'current'
            elif variant == 'sdk':
                expected = True
            cases.append((variant, kind, (RAW if variant == 'sdk' else CURRENT)+MESSAGES+body, expected))
    flags = ['/nologo', '/std:c++20', '/EHsc', '/Zc:__cplusplus', '/Zc:preprocessor', '/utf-8', '/sdl', '/MT', '/c',
             '/DWIN32', '/D_WINDOWS', '/DWIN32_LEAN_AND_MEAN', '/DNOMINMAX',
             '/D_WIN32_WINNT=0x0A00', '/D_WIN32_IE=0x0A00', '/D_UNICODE', '/DUNICODE']
    try:
        for compiler in ('clang-cl', 'cl'):
            for variant, kind, text, expected_ok in cases:
                name = variant+'_'+kind
                if shutil.disk_usage(out).free < 1342177280:
                    raise RuntimeError('Disk reserve violated')
                src = out/(name+'.cpp')
                src.write_text(text, encoding='utf-8')
                command = [tools[compiler], *flags, '/I'+str(roots[variant]/'compat/mingw'), '/I'+str(roots[variant])]
                if compiler == 'clang-cl':
                    command.append('/clang:-ferror-limit=12')
                command += [str(src), '/Fo'+str(out/(compiler+'-'+name+'.obj'))]
                q = subprocess.run(command, cwd=out, capture_output=True, text=True,
                                   errors='replace', timeout=60)
                log = q.stdout+q.stderr
                label = compiler+'-'+name
                (out/(label+'.log')).write_text(log, encoding='utf-8')
                row = {'compiler': compiler, 'case': name, 'command': command,
                       'source_sha256': hashlib.sha256(src.read_bytes()).hexdigest(),
                       'exit': q.returncode, 'expected_ok': expected_ok,
                       'matched': expected_ok is None or (q.returncode == 0) == expected_ok, 'log': label+'.log'}
                result['cases'].append(row)
                save()
        assert all(row['matched'] for row in result['cases']), 'Unexpected control/case result'
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
