"""Held, bounded packaged GUI observation. Execute only on the reserved Linux runner."""
import hashlib, json, os, shutil, socket, subprocess, tarfile, time, urllib.request
from pathlib import Path
provenance=json.loads((Path(os.environ['GITHUB_WORKSPACE'])/'candidate-input/provenance.json').read_text())
assert provenance['gui_observation_allowed'] is True
os.environ['BTX_CANDIDATE_SHA256']=provenance['candidate_archive_sha256']
from result_handling import ARCHIVE, verdict

def main():
    assert os.environ.get('BTX_RUN_ATLAS_WINDOW') == 'explicit-native-authorisation'
    import ui  # Deliberately not imported by offline result tests.
    w = Path(os.environ['GITHUB_WORKSPACE'])
    out = w/'atlas-window-results'; out.mkdir(exist_ok=True)
    runtime = w/'atlas-window-runtime'
    package = None; owned = False; app = node = qtapp = None; handles = []
    state = {'profile': 'Ubuntu24 x86_64 virtual X11; Modelnet/wallet disabled local regtest'}
    def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
    def files(): return {str(f.relative_to(package)): digest(f) for f in package.rglob('*') if f.is_file()}
    def package_processes():
        rows = []
        if package:
            for p in Path('/proc').iterdir():
                if p.name.isdigit():
                    try:
                        if Path(os.readlink(p/'exe')).is_relative_to(package): rows.append(int(p.name))
                    except OSError: pass
        return rows
    def start(args, label, env):
        log = (out/(label+'.log')).open('wb'); handles.append(log)
        return subprocess.Popen(list(map(str,args)), env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    def capture(label):
        path = out/(label+'.png')
        subprocess.run(['scrot', str(path)], check=True, timeout=10)
        return {'file':path.name, 'sha256':digest(path)}
    def rpc(method):
        # The cookie stays in private runtime and never enters result files or argv.
        return json.loads(subprocess.check_output([str(package/'bin/btx-cli'),'-regtest',
                    '-datadir='+str(runtime/'node'), '-rpcport='+str(port),method], timeout=10))
    try:
        assert shutil.disk_usage(w).free > 3*1024**3
        assert not runtime.exists(); runtime.mkdir(mode=0o700); owned=True
        for name in ('home','node'): (runtime/name).mkdir(mode=0o700)
        env=dict(os.environ, HOME=str(runtime/'home'), XDG_CONFIG_HOME=str(runtime/'home/config'),
                 XDG_DATA_HOME=str(runtime/'home/data'), XDG_CACHE_HOME=str(runtime/'home/cache'),
                 NO_AT_BRIDGE='0', GTK_MODULES='atk-bridge')
        archive=runtime/'release.tar.gz'
        shutil.copyfile(w/'candidate-input/btx-linux-gui-candidate.tar.gz',archive)
        state['archive_sha256']=digest(archive)
        assert state['archive_sha256']==ARCHIVE
        with (out/'normal-archive-gate.log').open('wb') as gate_log:
            gate=subprocess.run(['/usr/bin/python3',Path(__file__).with_name('verify_release_btxd.py'),'--archive',archive,'--require-model-helpers'],stdout=gate_log,stderr=subprocess.STDOUT,timeout=180)
        assert gate.returncode==0,'Normal archive gate failed before GUI'
        state['normal_gate_pass']=True
        state['candidate_provenance']={'source':provenance['source']}
        state['reconstructed_candidate']=False
        state['release_qualified']=False
        dest=runtime/'package';dest.mkdir()
        with tarfile.open(archive) as t:
            assert sum(m.size for m in t.getmembers()) < 2*1024**3
            t.extractall(dest,filter='data')
        roots=list(dest.rglob('bin/btx-atlas'));assert len(roots)==1
        package=roots[0].parent.parent
        state['package_before']=files()
        assert state['package_before']=={n:v['sha256'] for n,v in provenance['candidate_files'].items()}, 'Candidate extraction differs from assembly manifest'
        assert not package_processes()
        # Trace an optional host display prerequisite before node/app execution.
        import re
        qt_loader_env=dict(env,LD_LIBRARY_PATH=str(package/'lib/qt-private')+':'+str(package/'lib'))
        plugin=package/'lib/qt-private/qt6/plugins/platforms/libqxcb.so'
        probe=subprocess.run(['ldd',str(plugin)],env=qt_loader_env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=20)
        (out/'qt-plugin-before.log').write_text(probe.stdout)
        missing=re.findall(r'^\s*(\S+) => not found',probe.stdout,re.M)
        state['qt_plugin_missing_before']=sorted(set(missing))
        if missing:
            # Only this declared host library may be supplied; any other missing dependency stops the recipe.
            assert set(missing)=={'libxkbcommon-x11.so.0'},'Unexpected host display dependency'
            with (out/'host-display-prerequisite.log').open('wb') as log:
                installed=subprocess.run(['sudo','apt-get','install','-y','--no-install-recommends','libxkbcommon-x11-0'],stdout=log,stderr=subprocess.STDOUT,timeout=120)
            assert installed.returncode==0
            after=subprocess.check_output(['ldd',str(plugin)],env=qt_loader_env,text=True,stderr=subprocess.STDOUT,timeout=20)
            (out/'qt-plugin-after.log').write_text(after)
            assert 'not found' not in after
        with socket.socket() as sock: sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        node=start([package/'bin/btxd','-regtest','-datadir='+str(runtime/'node'),'-server=1',
                    '-rpcbind=127.0.0.1','-rpcallowip=127.0.0.1','-rpcport='+str(port),
                    '-listen=0','-connect=0','-dnsseed=0','-discover=0','-natpmp=0',
                    '-disablewallet=1','-modelnet=0','-dbcache=32','-printtoconsole=1'], 'node', env)
        end=time.monotonic()+45
        while True:
            try:
                chain=rpc('getblockchaininfo');break
            except Exception:
                if node.poll() is not None or time.monotonic()>end: raise
                time.sleep(.5)
        state['rpc_control']={'chain':chain['chain'],'blocks':chain['blocks'],'peers':rpc('getconnectioncount')}
        assert state['rpc_control']=={'chain':'regtest','blocks':0,'peers':0}
        genesis=subprocess.check_output([str(package/'bin/btx-cli'),'-regtest','-datadir='+str(runtime/'node'),'-rpcport='+str(port),'getblockhash','0'],timeout=10,text=True).strip()
        # Independently observe intended Atlas resolution before GUI: private Qt libraries must not shadow host GTK/WebKit GLib/DBus.
        loader_env=dict(env,LD_LIBRARY_PATH=str(package/'lib'))
        resolved=subprocess.check_output(['ldd',str(package/'libexec/btx-atlas.real')],env=loader_env,text=True,stderr=subprocess.STDOUT,timeout=20)
        (out/'atlas-ldd.log').write_text(resolved)
        assert 'not found' not in resolved
        import re
        state['atlas_host_resolution']={}
        for soname in ('libglib-2.0.so.0','libdbus-1.so.3'):
            match=re.search(re.escape(soname)+r' => (/\S+)',resolved)
            assert match and not Path(match.group(1)).resolve().is_relative_to(package.resolve())
            state['atlas_host_resolution'][soname]=match.group(1)
        # Actual current Qt window, not old version-only evidence.
        (runtime/'qt').mkdir(mode=0o700)
        qtapp=start([package/'bin/btx-qt','-regtest','-datadir='+str(runtime/'qt'),'-listen=0','-connect=0','-dnsseed=0','-discover=0','-disablewallet=1','-modelnet=0','-splash=0','-dbcache=32'],'qt-main',env)
        def qt_window():
            return qtapp.poll() is None and '[regtest]' in subprocess.check_output(['wmctrl','-l'],text=True)
        ui.wait(qt_window,45);time.sleep(2)
        state['qt_window_text']=subprocess.check_output(['wmctrl','-l'],text=True)
        state['qt_main_image']=capture('qt-main')
        subprocess.run(['wmctrl','-c','[regtest]'],check=True,timeout=5);qtapp.wait(timeout=20)
        assert qtapp.returncode==0
        state['qt_window_pass']=True
        app=start([package/'bin/btx-atlas'],'atlas',env)
        ui.wait(lambda:'The node is the network.' in ui.text(),45)
        state['app_alive']=app.poll() is None
        state['launch_text']=ui.text(); state['launch_image']=capture('launch')
        ui.click('Connect to a local BTX node')
        endpoint='127.0.0.1:'+str(port)
        ui.wait(lambda:'Choose cookie and connect' in ui.text())
        ui.endpoint(endpoint);ui.click('Choose cookie and connect')
        ui.wait(lambda:"Choose this BTX node's RPC .cookie file" in ui.text())
        state['cookie_picker_text']=ui.text();state['cookie_picker_image']=capture('cookie-picker')
        ui.file_path(runtime/'node/regtest/.cookie')
        ui.wait(lambda:'Connect to local node' in ui.text())
        confirmation=ui.text()
        assert ('Endpoint: '+endpoint in confirmation and 'Chain: regtest' in confirmation
                and genesis in confirmation), 'Unexpected native connection target'
        state['native_confirmation_checked']=True
        state['native_confirmation_text']=confirmation
        state['native_confirmation_image']=capture('native-confirmation')
        ui.click('Ok')
        ui.wait(lambda:'LIVE LOCAL' in ui.text() and '0 blocks' in ui.text(),45)
        state['connected_observations']=[{'time':time.monotonic(),'text':ui.text()}]
        time.sleep(5)
        state['connected_observations'].append({'time':time.monotonic(),'text':ui.text()})
        state['connected_image']=capture('connected')
        assert app.poll() is None
    except TimeoutError as e:
        state['error']=str(e)  # Unavailable GUI evidence is incomplete, never success.
        try:
            state['last_gui_text']=ui.text()
            state['last_image']=capture('last-observation')
        except Exception as diagnostic_error:
            state['diagnostic_error']=repr(diagnostic_error)
    except Exception as e:
        state['error']=repr(e)
    finally:
        if app:
            state['app_crashed']=app.poll() is not None and app.returncode != 0
            if app.poll() is None:
                try: subprocess.run(['wmctrl','-c','BTX'],timeout=5,check=True);app.wait(timeout=10)
                except Exception: pass
        if node and node.poll() is None:
            try:
                subprocess.check_output([str(package/'bin/btx-cli'),'-regtest','-datadir='+str(runtime/'node'),'-rpcport='+str(port),'stop'],timeout=10)
                node.wait(timeout=15)
            except Exception: pass
        state['cleanup_signals']=[]
        # Only owned process groups; any fallback signal makes overall non-PASS.
        for proc in (qtapp,app,node):
            if proc and proc.poll() is None:
                import signal
                state['cleanup_signals'].append(proc.pid)
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=5)
        if package: state['package_after']=files()
        state['cleanup_remaining']=package_processes()
        for h in handles:h.close()
        if owned and not state['cleanup_remaining']:shutil.rmtree(runtime)
        state['runtime_removed']=owned and not runtime.exists()
        state.update(verdict(state,out))
        (out/'result.json').write_text(json.dumps(state,indent=2)+'\n')
    return 0 if state['overall']=='PASS' else 1

if __name__=='__main__': raise SystemExit(main())
