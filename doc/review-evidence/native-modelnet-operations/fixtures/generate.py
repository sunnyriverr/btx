#!/usr/bin/env python3
"""Extract unchanged source functions into one bounded before/after fixture."""
import hashlib, json, pathlib

HERE = pathlib.Path(__file__).resolve().parent
REPAIR = HERE.parent
SRC = REPAIR / 'source' / 'src'
manifest = {'scope': 'Exact extracted functions, not a complete translation-unit/project test',
            'fixture_config': {'HAVE_CLOSE_RANGE_GENERIC': 0, 'HAVE_CLOSE_RANGE_LINUX': 0,
                               'DISABLE_OPTIMIZED_SHA256': 1}, 'variants': {}}
prelude = r'''
#include <modelnet/generate.h>
#include <univalue.h>
#include <util/fs.h>
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <mutex>
#include <thread>
#include <vector>
#ifndef _WIN32
#include <crypto/common.h>
#include <crypto/sha256.h>
#include <util/strencodings.h>
#include <util/subprocess.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <sys/resource.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <sys/wait.h>
#include <unistd.h>
#ifdef __linux__
#include <sys/prctl.h>
#endif
#endif
// Logging is the only substituted dependency; it has no acceptance assertions.
template <typename... Args> void LogPrintf(const char*, const Args&...) {}
namespace modelnet {
'''

for variant in ('baseline', 'candidate'):
    texts = {name: (REPAIR / f'{variant}-{name}.cpp').read_text()
             for name in ('generate', 'pq1_runtime', 'helper')}
    entries = []
    def take(name, marker, stop=None):
        text = texts[name]
        begin = text.index(marker)
        end = text.index(stop, begin) if stop else text.index('\n}\n', begin) + 3
        chunk = text[begin:end]
        entries.append({'source': f'{variant}-{name}.cpp', 'marker': marker,
                        'first_line': text[:begin].count('\n') + 1,
                        'last_line': text[:end].count('\n'),
                        'sha256': hashlib.sha256(chunk.encode()).hexdigest()})
        return chunk
    chunks = [prelude, take('generate', 'bool IsExecutableFile('),
              take('generate', 'HostGenerateProfile ProbeHostGenerateProfile('),
              take('generate', 'UniValue HostGenerateProfileJson(')]
    # Keep the original CLI probe conditional, including candidate's guard.
    pq = texts['pq1_runtime']
    begin = pq.index('namespace {', pq.index('ConnLimits& GlobalConnLimits'))
    end = pq.index('void SetPq1SocketOpts', begin)
    chunk = pq[begin:end]
    entries.append({'source': f'{variant}-pq1_runtime.cpp', 'marker': 'OpensslCliHasMlKem768 + OpensslBin original conditional',
                    'first_line': pq[:begin].count('\n') + 1, 'last_line': pq[:end].count('\n'),
                    'sha256': hashlib.sha256(chunk.encode()).hexdigest()})
    chunks.append(chunk)
    chunks += [take('helper', 'bool StickyWorldWritableDir('),
               take('helper', 'bool LooksLikeTmpFallbackSock('),
               '#if !defined(WIN32) && !defined(__APPLE__)\n',
               take('helper', 'bool OwnerOnlyDir('), '#endif\n',
               take('helper', 'fs::path RuntimeSockDir('),
               take('helper', 'fs::path UnixRpcListenPath('),
               take('helper', 'bool UnixSocketSafeToAdopt('),
               take('helper', 'bool UnixConnectedPeerIsSelf('),
               take('helper', 'void CloseWorkerDescriptors(', 'int AddrConnectPreference('),
               take('helper', 'int ListenUnix('),
               '#ifndef _WIN32\n', take('pq1_runtime', 'bool WaitFd('),
               'constexpr int PQ1_IDLE_MS = 30000;\n',
               take('helper', 'std::string RecvUntil('), '#endif\n',
               'constexpr size_t MAX_RPC_BODY = 256 * 1024;\n',
               'constexpr int UNIX_RPC_REPLY_MS = 120 * 1000;\n',
               'constexpr int UNIX_RPC_LONG_REPLY_MS = 24 * 60 * 60 * 1000;\n',
               take('helper', 'int UnixRpcReplyTimeoutMs('),
               take('helper', 'bool CallUnixRpc('),
               take('helper', 'template <typename Writer>\nbool WritePrivatePem('),
               '} // namespace modelnet\n', (HERE / 'controls.cpp.in').read_text()]
    output = HERE / f'{variant}-controls.cpp'
    output.write_text('\n'.join(chunks))
    manifest['variants'][variant] = {'extractions': entries, 'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
                                   'source_sha256': {name: hashlib.sha256(text.encode()).hexdigest() for name,text in texts.items()}}
deps = ['util/fs.h', 'modelnet/generate.h', 'util/subprocess.h', 'util/subprocess.cpp',
        'crypto/sha256.cpp', 'crypto/hex_base.cpp', 'support/cleanse.cpp',
        'univalue/include/univalue.h'] + [str(p.relative_to(SRC)) for p in sorted((SRC/'univalue/lib').glob('*.cpp'))]
manifest['real_source_dependencies'] = {p: hashlib.sha256((SRC/p).read_bytes()).hexdigest() for p in deps}
manifest['harness_sha256'] = {p: hashlib.sha256((HERE/p).read_bytes()).hexdigest()
                            for p in ('generate.py','controls.cpp.in','build.py','run.py')}
(HERE/'input-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
(HERE/'bitcoin-build-config.h').write_text('// Fixture only: execute the real descriptor fallback loop and generic SHA.\n#define HAVE_CLOSE_RANGE_GENERIC 0\n#define HAVE_CLOSE_RANGE_LINUX 0\n#define DISABLE_OPTIMIZED_SHA256 1\n')
print('Generated baseline-controls.cpp, candidate-controls.cpp and input-manifest.json')
