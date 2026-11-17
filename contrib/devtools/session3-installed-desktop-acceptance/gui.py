"""Source-reviewed draft only: installed Qt/Atlas acceptance on disposable Ubuntu X11.

Adapted from Session 2 runtime/run.py, run 43499330842. No archive extraction,
dependency installation, build, model transfer, wallet creation or GUI injection.
The controller must verify and install the exact candidate before calling this.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import time


SOURCE = '074dac167c26c1e091198f691ed5727817dba88a'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def inventory(prefix):
    result = {}
    for path in sorted(prefix.rglob('*')):
        name = str(path.relative_to(prefix))
        if path.is_symlink():
            result[name] = {'symlink': os.readlink(path)}
        elif path.is_file():
            result[name] = {'sha256': digest(path), 'mode': path.stat().st_mode & 0o777}
    return result


def process(pid):
    p = Path('/proc') / str(pid)
    stat = (p / 'stat').read_text().rsplit(')', 1)[1].split()
    return {'pid': pid, 'ppid': int(stat[1]), 'session': int(stat[3]), 'start_ticks': stat[19],
            'exe': os.readlink(p / 'exe')}


def inside(path, parent):
    return Path(path).resolve().is_relative_to(parent)


def owned_processes(prefix):
    rows = []
    for path in Path('/proc').iterdir():
        if path.name.isdigit():
            try:
                row = process(int(path.name))
                if inside(row['exe'], prefix):
                    rows.append(row)
            except (OSError, ValueError):
                pass
    return rows


def window_rows(prefix, executable, pid, start_ticks, env):
    row = process(pid)
    # A packaged shell launcher retains its PID while locating dependencies,
    # then execs the real app. A pending launcher is not a ready GUI process.
    # The existing bounded wait must observe the exact app and start identity.
    expected = (prefix / 'libexec' / executable).resolve()
    if Path(row['exe']).resolve() != expected or row['start_ticks'] != start_ticks:
        return []
    lines = subprocess.check_output(['wmctrl', '-lp'], text=True, env=env, timeout=5).splitlines()
    return [line.split(None, 4) for line in lines if len(line.split(None, 4)) == 5
            and line.split(None, 4)[2] == str(pid)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    prefix, runtime, out = args.prefix.resolve(), args.runtime.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    state = {'overall': 'FAIL', 'compiled_source': SOURCE,
             'profile': 'Ubuntu24 x86_64 virtual X11; wallet-disabled offline regtest',
             'scope': 'Installed candidate Qt window and Atlas local observation only',
             'official_release_qualified': False, 'cleanup_signals': [],
             'cleanup_remaining': [], 'connected_observations': []}
    processes, handles, window_ids = {}, [], {}
    runtime_owned = False
    env = None
    port = None
    before = None

    def interrupted(signum, _frame):
        raise InterruptedError('Controller signal ' + str(signum))

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)

    def scoped_processes():
        if not runtime_owned:
            return []
        sessions = {child.pid for child in processes.values()}
        rows = []
        for path in Path('/proc').iterdir():
            if path.name.isdigit():
                try:
                    row = process(int(path.name))
                    if inside(row['exe'], prefix) or row['session'] in sessions:
                        rows.append(row)
                except (OSError, ValueError):
                    pass
        return rows

    def save():
        (out / 'result.json').write_text(json.dumps(state, indent=2) + '\n')

    def launch(args, label):
        handle = (out / (label + '.log')).open('wb')
        handles.append(handle)
        child = subprocess.Popen([str(a) for a in args], env=env, stdout=handle,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        processes[label] = child
        # Persist session ownership before UI work, so the parent can contain
        # host WebKit descendants even if this driver is forcibly terminated.
        leader = process(child.pid)
        state.setdefault('owned_sessions', []).append({
            'pid': leader['pid'], 'session': leader['session'],
            'start_ticks': leader['start_ticks'], 'label': label})
        pending = out / 'owned-sessions.json.tmp'
        pending.write_text(json.dumps(state['owned_sessions'], indent=2) + '\n')
        pending.replace(out / 'owned-sessions.json')
        return child

    def rpc(method, *params):
        return subprocess.check_output([str(prefix / 'bin/btx-cli'), '-regtest',
            '-datadir=' + str(runtime / 'node'), '-rpcport=' + str(port),
            '-rpcclienttimeout=5', method, *params], env=env, text=True, timeout=8).strip()

    def capture(label):
        path = out / (label + '.png')
        subprocess.run(['scrot', str(path)], env=env, check=True, timeout=10)
        return {'file': path.name, 'sha256': digest(path)}

    def windows(label):
        child = processes[label]
        leader = next(row for row in state['owned_sessions'] if row['label'] == label)
        executable = {'qt': 'btx-qt.real', 'atlas': 'btx-atlas.real'}[label]
        return window_rows(prefix, executable, child.pid, leader['start_ticks'], env)

    def close_window(label):
        found = windows(label)
        assert len(found) == 1, (label, 'window not uniquely owned')
        window_ids[label] = found[0][0]
        subprocess.run(['wmctrl', '-ic', found[0][0]], env=env, check=True, timeout=5)
        processes[label].wait(timeout=25)
        assert processes[label].returncode == 0, (label, 'abnormal close')

    try:
        assert prefix.is_absolute() and (prefix / 'bin/btx-atlas').is_file()
        assert not runtime.exists() and not inside(runtime, prefix) and not inside(prefix, runtime)
        assert not owned_processes(prefix), 'Installed prefix already has live processes'
        assert shutil.disk_usage(runtime.parent).free > 3 * 1024 ** 3
        runtime.mkdir(mode=0o700)
        runtime_owned = True
        for name in ('home', 'node', 'qt', 'config', 'data', 'cache'):
            (runtime / name).mkdir(mode=0o700)
        env = dict(os.environ, HOME=str(runtime / 'home'),
                   XDG_CONFIG_HOME=str(runtime / 'config'), XDG_DATA_HOME=str(runtime / 'data'),
                   XDG_CACHE_HOME=str(runtime / 'cache'), PYTHONDONTWRITEBYTECODE='1',
                   NO_AT_BRIDGE='0', GTK_MODULES='atk-bridge', LC_ALL='C.UTF-8')
        for name in ('LD_LIBRARY_PATH', 'LD_PRELOAD', 'BTX_MODELD', 'BTX_MODELHELPER',
                     'BTX_GUARDD', 'PYTHONHOME', 'PYTHONPATH'):
            env.pop(name, None)
        before = inventory(prefix)
        # Explicit host prerequisite audit, without installing replacements on failure.
        loader = dict(env, LD_LIBRARY_PATH=str(prefix / 'lib/qt-private') + ':' + str(prefix / 'lib'))
        plugin = prefix / 'lib/qt-private/qt6/plugins/platforms/libqxcb.so'
        resolved = subprocess.check_output(['ldd', str(plugin)], env=loader, text=True,
                                          stderr=subprocess.STDOUT, timeout=20)
        (out / 'qt-plugin-ldd.log').write_text(resolved)
        assert 'not found' not in resolved, 'Missing declared Qt display prerequisite'
        resolved = subprocess.check_output(['ldd', str(prefix / 'libexec/btx-atlas.real')],
            env=dict(env, LD_LIBRARY_PATH=str(prefix / 'lib')), text=True,
            stderr=subprocess.STDOUT, timeout=20)
        (out / 'atlas-ldd.log').write_text(resolved)
        assert 'not found' not in resolved
        state['atlas_host_resolution'] = {}
        for soname in ('libglib-2.0.so.0', 'libdbus-1.so.3'):
            match = re.search(re.escape(soname) + r' => (/\S+)', resolved)
            assert match and not inside(match.group(1), prefix), 'Atlas shadows host desktop library'
            state['atlas_host_resolution'][soname] = match.group(1)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        isolation = ['-regtest', '-listen=0', '-networkactive=0', '-connect=0',
                     '-dnsseed=0', '-discover=0', '-natpmp=0', '-disablewallet=1',
                     '-modelnet=0', '-dbcache=32']
        node = launch([prefix / 'bin/btxd', *isolation, '-datadir=' + str(runtime / 'node'),
            '-server=1', '-rpcbind=127.0.0.1', '-rpcallowip=127.0.0.1',
            '-rpcport=' + str(port), '-printtoconsole=1'], 'node')
        deadline = time.monotonic() + 45
        while True:
            try:
                chain = json.loads(rpc('getblockchaininfo'))
                break
            except (OSError, ValueError, subprocess.SubprocessError):
                if node.poll() is not None or time.monotonic() > deadline:
                    raise
                time.sleep(.5)
        state['rpc_control'] = {'chain': chain['chain'], 'blocks': chain['blocks'],
                                'peers': json.loads(rpc('getconnectioncount'))}
        assert state['rpc_control'] == {'chain': 'regtest', 'blocks': 0, 'peers': 0}
        node_record = process(node.pid)
        assert Path(node_record['exe']).resolve() == (prefix / 'libexec/btxd.real').resolve()
        state['node_process'] = node_record
        genesis = rpc('getblockhash', '0')
        assert re.fullmatch('[0-9a-f]{64}', genesis)
        import ui
        ui.DIAGNOSTIC_OUT = out
        qt = launch([prefix / 'bin/btx-qt', *isolation,
            '-datadir=' + str(runtime / 'qt'), '-splash=0'], 'qt')
        ui.wait(lambda: qt.poll() is None and any('[regtest]' in row[4] for row in windows('qt')), 45)
        state['qt_main_image'] = capture('qt-main')
        state['qt_process'] = process(qt.pid)
        close_window('qt')
        state['qt_window_pass'] = True
        app = launch([prefix / 'bin/btx-atlas'], 'atlas')
        ui.wait(lambda: app.poll() is None and 'The node is the network.' in ui.text(), 45)
        state['launch_image'] = capture('launch')
        state['atlas_process'] = process(app.pid)
        assert inside(state['atlas_process']['exe'], prefix)
        ui.click('Connect to a local BTX node')
        endpoint = '127.0.0.1:' + str(port)
        ui.wait(lambda: 'Choose cookie and connect' in ui.text())
        ui.endpoint(endpoint)
        ui.click('Choose cookie and connect')
        ui.wait(lambda: "Choose this BTX node's RPC .cookie file" in ui.text())
        state['cookie_picker_image'] = capture('cookie-picker')
        ui.file_path(runtime / 'node/regtest/.cookie')
        ui.wait(lambda: 'Connect to local node' in ui.text())
        confirmation = ui.text()
        assert 'Endpoint: ' + endpoint in confirmation and 'Chain: regtest' in confirmation
        assert genesis in confirmation, 'Native confirmation targets a different node'
        state['native_confirmation_target'] = {'endpoint': endpoint, 'chain': 'regtest',
                                               'genesis': genesis}
        state['native_confirmation_checked'] = True
        state['native_confirmation_image'] = capture('native-confirmation')
        ui.click('Ok')
        ui.wait(lambda: 'LIVE LOCAL' in ui.text() and '0 blocks' in ui.text(), 45)
        for observation in range(2):
            if observation:
                time.sleep(5)
            observed = ui.text()
            assert app.poll() is None and 'LIVE LOCAL' in observed and '0 blocks' in observed
            assert 'regtest' in observed
            state['connected_observations'].append({'time': time.monotonic(), 'text': observed})
        state['connected_image'] = capture('connected')
        (out / 'atlas-loaded-maps.log').write_text((Path('/proc') / str(app.pid) / 'maps').read_text())
        close_window('atlas')
        assert rpc('stop')
        node.wait(timeout=25)
        assert node.returncode == 0
        state['normal_shutdown_pass'] = True
    except Exception as error:
        state['error'] = repr(error)
    finally:
        # Best-effort normal cleanup first. Exact owned windows, never global BTX title.
        for label in ('atlas', 'qt'):
            child = processes.get(label)
            if child and child.poll() is None:
                try:
                    close_window(label)
                except Exception as error:
                    state.setdefault('cleanup_errors', []).append((label, repr(error)))
        node = processes.get('node')
        if node and node.poll() is None:
            try:
                rpc('stop')
                node.wait(timeout=25)
            except Exception as error:
                state.setdefault('cleanup_errors', []).append(('node', repr(error)))
        # Fallbacks only target exact installed-prefix PID/start identity observations.
        # Any fallback is a failure, even if it leaves no process behind.
        for sig in (signal.SIGTERM, signal.SIGKILL):
            for row in scoped_processes():
                try:
                    now = process(row['pid'])
                    if now == row:
                        os.kill(row['pid'], sig)
                        state['cleanup_signals'].append({'process': row, 'signal': int(sig)})
                except OSError:
                    pass
            if scoped_processes():
                time.sleep(3)
        for child in processes.values():
            try:
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
        state['cleanup_remaining'] = scoped_processes()
        state['package_unchanged'] = before is not None and before == inventory(prefix)
        for handle in handles:
            handle.close()
        if runtime_owned and not state['cleanup_remaining']:
            shutil.rmtree(runtime)
        state['runtime_removed'] = runtime_owned and not runtime.exists()
        if (not state.get('error') and state.get('qt_window_pass')
                and state.get('native_confirmation_checked')
                and len(state['connected_observations']) == 2
                and state.get('normal_shutdown_pass') and state['package_unchanged']
                and state['runtime_removed'] and not state['cleanup_remaining']
                and not state['cleanup_signals'] and not state.get('cleanup_errors')):
            state['overall'] = 'PASS'
        save()
    return 0 if state['overall'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
