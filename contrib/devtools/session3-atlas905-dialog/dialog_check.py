"""Future actual native-dialog observation. Source-only until authorized."""
import hashlib
import ctypes
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import traceback
import pyatspi
from gi.repository import GLib
from fixture_data import MODEL_ID, PROFILE_ID, OPERATIONS

HERE = Path(__file__).resolve().parent
PIN = json.loads((HERE / 'INPUTS.json').read_text())
TITLE = 'Review local model intervention'
OBSERVATION_ERRORS = []


def observed_name(node):
    # File chooser trees can replace accessibles between enumeration and reads.
    # Skip an unreadable observation, never replay an action or accept missing text.
    try:
        return node.name or ''
    except GLib.Error as error:
        if len(OBSERVATION_ERRORS) < 20:
            OBSERVATION_ERRORS.append({'read': 'name', 'class': type(error).__name__,
                                       'message': str(error)[:1000]})
        return ''


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def process_row(pid):
    directory = Path('/proc') / str(pid)
    try:
        if directory.stat().st_uid != os.getuid():
            return None
        raw = (directory / 'stat').read_text()
    except FileNotFoundError:
        return None
    # comm is parenthesized and may contain spaces or parentheses.
    fields = raw.rsplit(')', 1)[1].split()
    return {'pid': int(pid), 'state': fields[0], 'ppid': int(fields[1]),
            'pgrp': int(fields[2]), 'session': int(fields[3]),
            'start_ticks': int(fields[19])}


def owned_processes(session_id):
    result = []
    for directory in Path('/proc').iterdir():
        if directory.name.isdecimal():
            row = process_row(int(directory.name))
            # Subreaper-adopted children are also this controller's own children.
            if row and (row['session'] == session_id or row['ppid'] == os.getpid()):
                result.append(row)
    return sorted(result, key=lambda row: row['pid'])


def enable_subreaper():
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl.argtypes = [ctypes.c_int] + [ctypes.c_ulong] * 4
    libc.prctl.restype = ctypes.c_int
    if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        raise OSError(ctypes.get_errno(), 'Cannot admit owned-child reaping')


def stop_owned_processes(child, state, save):
    state['cleanup_snapshots'] = []
    state['reaped_helpers'] = []
    for sig, grace in ((signal.SIGTERM, 10), (signal.SIGKILL, 5)):
        deadline = time.monotonic() + grace
        signalled = set()
        first_snapshot = True
        while time.monotonic() < deadline:
            child.poll()  # Popen owns and reaps its direct child.
            rows = owned_processes(child.pid)
            for row in rows:
                if row['pid'] != child.pid and row['ppid'] == os.getpid() and row['state'] == 'Z':
                    try:
                        pid, status = os.waitpid(row['pid'], os.WNOHANG)
                        if pid:
                            state['reaped_helpers'].append({'pid': pid, 'wait_status': status})
                    except ChildProcessError:
                        pass  # Rescan; this never counts as cleanup success.
            rows = owned_processes(child.pid)
            if first_snapshot or len(state['cleanup_snapshots']) < 30:
                state['cleanup_snapshots'].append({'signal': sig.name, 'members': rows})
                first_snapshot = False
                save()
            if not rows and child.poll() is not None:
                state['cleanup_remaining'] = []
                return True
            for row in rows:
                identity = (row['pid'], row['start_ticks'])
                if row['state'] == 'Z' or identity in signalled:
                    continue
                try:
                    fd = os.pidfd_open(row['pid'], 0)
                    try:
                        current = process_row(row['pid'])
                        if (current and current['start_ticks'] == row['start_ticks']
                                and (current['session'] == child.pid or current['ppid'] == os.getpid())):
                            signal.pidfd_send_signal(fd, sig)
                            signalled.add(identity)
                    finally:
                        os.close(fd)
                except ProcessLookupError:
                    pass
            time.sleep(0.1)
    child.poll()
    state['cleanup_remaining'] = owned_processes(child.pid)
    return not state['cleanup_remaining'] and child.poll() is not None


def nodes(root=None):
    found = []
    def visit(node, depth=0):
        if depth > 35 or len(found) >= 8000:
            return
        try:
            if node.getState().contains(pyatspi.STATE_SHOWING):
                found.append(node)
            for child in node:
                if child is not None:
                    visit(child, depth + 1)
        except Exception:
            pass
    visit(root if root is not None else pyatspi.Registry.getDesktop(0))
    return found


def text(root=None):
    result = []
    for node in nodes(root):
        result.append(observed_name(node))
        try:
            content = node.queryText()
            result.append(content.getText(0, min(content.characterCount, 20000)))
        except Exception:
            pass
    return '\n'.join(result)


def main():
    records = Path(os.environ['RECORDS']).resolve()
    binary = Path(os.environ['RUNNER_TEMP']).resolve() / 'session3-atlas905-dialog-binary/btx-atlas'
    state = {'status': 'NOT_QUALIFIED', 'stage': 'admission', 'input_scope': 'controlled read-only worker',
             'GUI_case': 'long review then Cancel', 'signature_or_activation_qualified': False}
    child = None
    handle = None
    clean = False
    runtime = None
    start = time.monotonic()
    def save():
        temporary = records / 'dialog-result.tmp'
        temporary.write_text(json.dumps(state, indent=2) + '\n')
        temporary.replace(records / 'dialog-result.json')
    def interrupted(signum, frame):
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, signal.SIG_IGN)
        state['interrupt_signal'] = signum
        raise InterruptedError('owned UI check interrupted')
    def step(label):
        state['step'] = label
        save()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, interrupted)
    def wait(predicate, limit=30):
        end = min(time.monotonic() + limit, start + PIN['UI_deadline_seconds'])
        while time.monotonic() < end:
            if child is not None and child.poll() is not None:
                raise RuntimeError('Atlas exited before observation')
            if predicate():
                return
            time.sleep(0.25)
        raise TimeoutError('UI observation deadline')
    def windows(title=None, portal=False):
        query = subprocess.run(['wmctrl', '-lp'], text=True, capture_output=True, timeout=5)
        state['window_query_attempts'] = state.get('window_query_attempts', 0) + 1
        if query.returncode:
            state['last_window_query_error'] = {'returncode': query.returncode,
                                               'stderr': query.stderr[:1000]}
            # Openbox may not publish a client list until the first mapped window.
            # Only that exact startup condition is retryable, within ten seconds.
            if (query.returncode == 1 and not query.stdout.strip()
                    and query.stderr.strip() == 'Cannot get client list properties.'
                    and time.monotonic() - launched_at < 10):
                return []
            raise RuntimeError('window query failed; inspect last_window_query_error')
        rows = query.stdout.splitlines()
        result = []
        for row in rows:
            fields = row.split(None, 4)
            if len(fields) != 5 or (title is not None and title not in fields[4]):
                continue
            pid = fields[2]
            owned = pid == str(child.pid)
            if not owned and pid.isdecimal():
                proc = Path('/proc') / pid
                try:
                    owned = (proc.stat().st_uid == os.getuid()
                             and (proc / 'exe').resolve().name == 'zenity'
                             and os.getpgid(int(pid)) == child.pid)
                except (OSError, ProcessLookupError):
                    owned = False
            if portal and not owned and pid.isdecimal():
                proc = Path('/proc') / pid
                try:
                    owned = (proc.stat().st_uid == os.getuid()
                             and (proc / 'exe').resolve().name == 'xdg-desktop-portal-gtk')
                except OSError:
                    owned = False
            if owned:
                result.append(fields)
        return result
    def dialog(title):
        assert len(windows(title)) == 1
        roots = [n for n in nodes() if n.getRoleName() in {'dialog', 'alert', 'frame'}
                 and title in (n.name or '')]
        assert len(roots) == 1, 'native dialog accessibility not unique'
        return roots[0]
    def action(name, root=None, roles=None):
        candidates = [n for n in nodes(root) if (n.name or '').replace('_', '') == name
                      and n.getRoleName() in (roles or {'push button', 'button', 'link'})]
        assert len(candidates) == 1, 'control not unique'
        n = candidates[0]
        assert n.getState().contains(pyatspi.STATE_ENABLED)
        a = n.queryAction()
        assert a.nActions and a.doAction(0)
    def choose_file(title, path):
        step('picker:wait_owned_window:' + title)
        wait(lambda: len(windows(title, portal=True)) == 1)
        window = windows(title, portal=True)[0][0]
        step('picker:focus:' + title)
        subprocess.run(['xdotool', 'windowactivate', '--sync', window], check=True, timeout=5)
        step('picker:open_location:' + title)
        subprocess.run(['xdotool', 'key', '--clearmodifiers', 'ctrl+l'], check=True, timeout=5)
        step('picker:type_path:' + title)
        subprocess.run(['xdotool', 'type', '--clearmodifiers', '--', str(path)], check=True, timeout=5)
        step('picker:observe_entered_path:' + title)
        wait(lambda: str(path) in text(), 10)
        # Pressing Enter accepts the path in this uniquely observed file chooser.
        step('picker:accept_path:' + title)
        subprocess.run(['xdotool', 'key', '--clearmodifiers', 'Return'], check=True, timeout=5)
        step('picker:wait_closed:' + title)
        wait(lambda: not windows(title, portal=True), 10)
        state.pop('step', None)
        save()
    def select(name):
        step('selector:focus:' + name)
        candidates = [n for n in nodes() if observed_name(n) == name and n.getRoleName() == 'combo box']
        assert len(candidates) == 1
        assert candidates[0].queryComponent().grabFocus()
        # Select the only fixture item, then blur; do not inspect option labels
        # that this WebKit accessibility tree did not expose in prior runs.
        step('selector:choose_only_fixture_item:' + name)
        subprocess.run(['xdotool', 'key', '--clearmodifiers', 'Home', 'Down', 'Tab'], check=True, timeout=5)
        state.pop('step', None)
        save()
    def keyboard_profile_summary(phase):
        step('profile_summary:locate_focusable:' + phase)
        candidates = []
        for node in nodes():
            if observed_name(node) != 'Exact source result':
                continue
            states = node.getState()
            if states.contains(pyatspi.STATE_ENABLED) and states.contains(pyatspi.STATE_FOCUSABLE):
                candidates.append(node)
        assert len(candidates) == 1, 'focusable profile summary not unique'
        node = candidates[0]
        observation = {'phase': phase, 'method': 'focused keyboard', 'key': 'space'}
        state.setdefault('profile_summary_keyboard', []).append(observation)
        step('profile_summary:focus:' + phase)
        observation['focus_return'] = bool(node.queryComponent().grabFocus())
        save()
        assert observation['focus_return'], 'profile summary refused keyboard focus'
        wait(lambda: node.getState().contains(pyatspi.STATE_FOCUSED), 5)
        observation['focus_observed'] = True
        step('profile_summary:press_space_once:' + phase)
        # HTMLSummaryElement handles one Space down/up as its normal activation.
        # Never fall back to doAction or repeat a key after an unknown outcome.
        subprocess.run(['xdotool', 'key', '--clearmodifiers', 'space'], check=True, timeout=5)
        observation['key_command_completed'] = True
        save()
    def reveal_action(name):
        # Read-only page scrolling, bounded; never click a guessed coordinate.
        step('selection_proof:reveal_action:' + name)
        deadline = min(time.monotonic() + 10, start + PIN['UI_deadline_seconds'])
        for _ in range(12):
            if time.monotonic() >= deadline:
                break
            if any(observed_name(n) == name and n.getRoleName() in {'push button', 'button'} for n in nodes()):
                state.pop('step', None)
                save()
                return
            subprocess.run(['xdotool', 'key', '--clearmodifiers', 'Next'], check=True,
                           timeout=max(0.1, min(5, deadline - time.monotonic())))
            time.sleep(0.2)
        raise TimeoutError('Required action was not revealed by bounded scrolling')
    def screenshot(name):
        path = records / (name + '.png')
        subprocess.run(['scrot', str(path)], check=True, timeout=10)
        state.setdefault('screenshots', []).append({'file': path.name, 'sha256': sha(path)})
    def calls(data):
        found = list(data.rglob('fixture-calls.jsonl'))
        assert len(found) <= 1
        return [] if not found else [json.loads(x) for x in found[0].read_text().splitlines()]
    try:
        save()
        assert sys.platform == 'linux' and sha(binary) == PIN['binary_sha256']
        assert os.environ.get('DISPLAY') and os.environ.get('DBUS_SESSION_BUS_ADDRESS')
        state['stage'] = 'window_manager_readiness'
        save()
        wm_pid = int(os.environ['ATLAS905_WM_PID'])
        def manager_ready():
            os.kill(wm_pid, 0)  # The workflow owns this Openbox PID, not a peer UI.
            query = subprocess.run(['wmctrl', '-m'], text=True, capture_output=True, timeout=5)
            state['last_window_manager_probe'] = {'returncode': query.returncode,
                                                 'stdout': query.stdout[:2000],
                                                 'stderr': query.stderr[:1000]}
            return query.returncode == 0 and 'Name: Openbox' in query.stdout.splitlines()
        wait(manager_ready, 15)
        state['window_manager_ready'] = True
        save()
        runtime = Path(tempfile.mkdtemp(prefix='atlas905-ui-', dir=os.environ['RUNNER_TEMP']))
        home, config, data, cache = [runtime / x for x in ('home', 'config', 'data', 'cache')]
        for directory in (home, config, data, cache):
            directory.mkdir(mode=0o700)
        worker = runtime / 'controlled-worker'
        worker.mkdir()
        for name in ('worker.py', 'fixture_data.py'):
            shutil.copy2(HERE / name, worker / name)
        (worker / 'btx_neuronlab').mkdir()
        (worker / 'btx_neuronlab/__init__.py').write_text('')
        file_hashes = {name: sha(worker / name) for name in
                      ('worker.py', 'fixture_data.py', 'btx_neuronlab/__init__.py')}
        manifest = worker / 'code-manifest.json'
        manifest.write_text(json.dumps({'schema': 'btx.neuronlab.code-manifest/1',
                                        'files': file_hashes}, sort_keys=True) + '\n')
        interpreter = Path(os.environ['WORKER_PYTHON']).resolve()
        assert interpreter.is_file() and not interpreter.is_symlink()
        env = {**os.environ, 'HOME': str(home), 'XDG_CONFIG_HOME': str(config),
               'XDG_DATA_HOME': str(data), 'XDG_CACHE_HOME': str(cache),
               'NO_AT_BRIDGE': '0', 'GTK_MODULES': 'atk-bridge', 'LC_ALL': 'C.UTF-8',
               'LIBGL_ALWAYS_SOFTWARE': '1', 'WEBKIT_DISABLE_DMABUF_RENDERER': '1'}
        for name in ('GH_TOKEN', 'GITHUB_TOKEN', 'PYTHONHOME', 'PYTHONPATH', 'LD_PRELOAD', 'LD_LIBRARY_PATH'):
            env.pop(name, None)
        state.update(stage='admit_owned_cleanup', binary_sha256=sha(binary), source=PIN['source'])
        assert hasattr(os, 'pidfd_open') and hasattr(signal, 'pidfd_send_signal')
        enable_subreaper()
        state['subreaper_enabled'] = True
        state.update(stage='launch', launch_intent=True)
        save()
        handle = (records / 'atlas.log').open('wb')
        child = subprocess.Popen([str(binary)], env=env, stdout=handle,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        launched_at = time.monotonic()
        state['owned_session'] = child.pid
        save()
        wait(lambda: len(windows()) >= 1)
        assert Path('/proc/' + str(child.pid) + '/exe').resolve() == binary
        wait(lambda: any(n.name == 'Neuron Lab' and n.getRoleName() in {'link', 'button', 'push button'} for n in nodes()))
        action('Neuron Lab')
        wait(lambda: 'Configure worker' in text())
        state['stage'] = 'controlled_worker_setup'
        save()
        action('Configure worker')
        choose_file('Choose a trusted Python', interpreter)
        choose_file('Choose installed contrib/atlas/neuronlab/worker.py', worker / 'worker.py')
        wait(lambda: len(windows('Install local scientific worker')) == 1)
        setup = dialog('Install local scientific worker')
        setup_text = text(setup)
        assert sha(interpreter) in setup_text and sha(manifest) in setup_text
        assert str(worker / 'worker.py') in setup_text
        # The sole OK is the explicitly described disposable fixture setup.
        action('Ok', setup)
        completed = 'Local operation completed. Inspect the exact result and its qualification limits below.'
        step('worker_setup:wait_completed_refresh')
        wait(lambda: completed in text()
             and {'status', 'models', 'list'} <= {c['action'] for c in calls(data) if c['allowed']})
        select('Exact registered model')
        step('selection_proof:rendered_model_binding')
        expected_binding = 'BTXTinyLM · 2 layers · 32 MLP coordinates/layer · gelu'
        wait(lambda: expected_binding in text(), 10)
        state['rendered_model_binding_checked'] = True
        screenshot('selected-model')
        select('Signed profile')
        step('selection_proof:profile_request_completed')
        wait(lambda: any(c['action'] == 'profile' for c in calls(data)) and completed in text())
        action('Sharing & trust')
        step('selection_proof:expand_rendered_profile_summary')
        wait(lambda: any(observed_name(n) == 'Exact source result' for n in nodes()), 10)
        keyboard_profile_summary('expand')
        wait(lambda: PROFILE_ID in text() and 'CONTROLLED 905 dialog fixture' in text()
             and 'SYNTHETIC_NO_SIGNATURE' in text() and 'CONTROLLED_UI_DATA' in text(), 10)
        state['rendered_profile_identity_checked'] = PROFILE_ID
        screenshot('selected-profile-identity')
        step('selection_proof:collapse_profile_summary')
        keyboard_profile_summary('collapse')
        step('profile_summary:observe_collapsed_content')
        def collapsed_summary_visible():
            screen = text()
            return 'Exact source result' in screen and 'SYNTHETIC_NO_SIGNATURE' not in screen
        wait(collapsed_summary_visible, 5)
        state['profile_summary_keyboard_collapsed'] = True
        reveal_action('Enable for local adapter')
        state['stage'] = 'target_review'
        save()
        action('Enable for local adapter')
        wait(lambda: len(windows(TITLE)) == 1)
        target = dialog(TITLE)
        actual = text(target)
        before = calls(data)
        inspections = [c for c in before if c['operation_id'].endswith('-inspect')]
        assert len(inspections) == 1
        operation_id = inspections[0]['operation_id'][:-8]
        payload = {'profile_id': PROFILE_ID, 'model_id': MODEL_ID, 'expected_generation': 0}
        pretty_request = json.dumps(payload, sort_keys=True, indent=2)
        assert len(pretty_request) <= 400, 'Expected full request must fit the native preview'
        request_digest = hashlib.sha256(pretty_request.encode()).hexdigest()
        pretty_operators = json.dumps(OPERATIONS, sort_keys=True, indent=2)
        compact_operators = json.dumps(OPERATIONS, sort_keys=True, separators=(',', ':'))
        required = ['Research action: activate', 'Operation ID: ' + operation_id,
                    'Signed operators: 20', compact_operators[:300] + ' ...',
                    pretty_request, 'SHA-256: ' + request_digest,
                    'Operators SHA-256: ' + hashlib.sha256(pretty_operators.encode()).hexdigest()]
        assert all(piece in actual for piece in required)
        (records / 'selection-proof.json').write_text(json.dumps({
            'rendered_model_binding': expected_binding, 'rendered_profile_id': PROFILE_ID,
            'expected_request': payload, 'expected_request_sha256': request_digest,
            'exact_request_and_digest_observed_in_native_review': True,
            'proof_scope': 'controlled presentation identity, not signatures or activation'
        }, indent=2) + '\n')
        assert 'Exact signed operators:' not in actual, 'long-review case did not compact'
        # Accessibility geometry is an automated gate, not a human visual verdict.
        buttons = [n for n in nodes(target) if n.getRoleName() in {'push button', 'button'}
                   and (n.name or '').replace('_', '') in {'Cancel', 'Ok'}]
        assert {(n.name or '').replace('_', '') for n in buttons} == {'Cancel', 'Ok'}
        for n in buttons:
            assert n.getState().contains(pyatspi.STATE_ENABLED)
            x, y, width, height = n.queryComponent().getExtents(pyatspi.DESKTOP_COORDS)
            assert width > 0 and height > 0 and x >= 0 and y >= 0
            assert x + width <= PIN['screen'][0] and y + height <= PIN['screen'][1]
        (records / 'native-review-text.txt').write_text(actual)
        screenshot('long-native-review')
        action('Cancel', target)
        wait(lambda: not windows(TITLE))
        wait(lambda: 'Cancelled in the native confirmation dialog' in text())
        time.sleep(2)
        after = calls(data)
        assert after == before and all(c['allowed'] for c in after)
        assert not any(c['action'] in {'activate', 'compare', 'generate'} for c in after)
        assert all(sha(worker / name) == value for name, value in file_hashes.items())
        assert sha(binary) == PIN['binary_sha256']
        (records / 'fixture-calls.json').write_text(json.dumps(after, indent=2) + '\n')
        screenshot('cancelled-native-review')
        state.update(status='PASS_AUTOMATED_DIALOG_CANCEL_PENDING_VISUAL_REVIEW', stage='complete',
                     operator_count=20, native_request_digest_checked=True,
                     native_operator_digest_checked=True, buttons_inside_screen=True,
                     Cancel_observed=True, worker_mutation_requests=0,
                     actual_signed_profile_verified=False, requires_screenshot_review=True)
    except Exception as error:
        state.update(status='NOT_QUALIFIED', error_class=type(error).__name__,
                     error_message=str(error)[:2000], failed_step=state.get('step', state['stage']),
                     error_traceback=traceback.format_exc(limit=12)[-12000:])
        # Persist exact failure before best-effort accessibility/screenshot capture.
        save()
        if child is not None:
            try:
                (records / 'failure-ui-text.txt').write_text(text()[:100000])
                screenshot('failure-ui')
            except Exception:
                state['failure_capture'] = 'unavailable'
    finally:
        if runtime is not None:
            try:
                (records / 'fixture-calls-diagnostic.json').write_text(json.dumps(calls(data), indent=2) + '\n')
            except Exception as error:
                state['worker_call_capture_error'] = str(error)[:1000]
        if child is not None:
            # Do not call zombies "live", or assume group absence proves reaping.
            try:
                clean = stop_owned_processes(child, state, save)
            except Exception as error:
                state.update(cleanup_error_message=str(error)[:2000],
                             cleanup_error_traceback=traceback.format_exc(limit=12)[-12000:])
            if not clean:
                state['status'] = 'NOT_QUALIFIED'
            state['process_group_cleanup'] = clean
        if handle is not None:
            handle.close()
        if runtime is not None and (child is None or clean):
            try:
                shutil.rmtree(runtime)
                state['scratch_removed'] = not runtime.exists()
            except Exception as error:
                state.update(status='NOT_QUALIFIED', scratch_error_class=type(error).__name__)
        elif runtime is not None:
            state.update(status='NOT_QUALIFIED', scratch_removed=False)
        state['elapsed_seconds'] = round(time.monotonic() - start, 3)
        state['observation_errors_sample'] = OBSERVATION_ERRORS
        save()
    return 0 if state['status'] == 'PASS_AUTOMATED_DIALOG_CANCEL_PENDING_VISUAL_REVIEW' and clean else 1


if __name__ == '__main__':
    sys.exit(main())
