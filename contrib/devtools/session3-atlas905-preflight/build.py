"""One bounded, offline Atlas-only compile; never launch the result."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
PIN = json.loads((HERE / 'INPUTS.json').read_text())


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()


def stop_group(process):
    process.poll()
    try:
        os.killpg(process.pid, 0)
    except ProcessLookupError:
        return True
    for sig, grace in [(signal.SIGTERM, 15), (signal.SIGKILL, 5)]:
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            return True
        end = time.monotonic() + grace
        while time.monotonic() < end:
            process.poll()
            try:
                os.killpg(process.pid, 0)
            except ProcessLookupError:
                return True
            time.sleep(0.1)
    return False


def main():
    workspace = Path(os.environ['GITHUB_WORKSPACE']).resolve()
    records = Path(os.environ['RECORDS']).resolve()
    atlas = workspace / 'product/gui/atlas'
    binary = workspace / 'atlas480-target/release/btx-atlas'
    result = {'status': 'FAIL_BUILD', 'compile_started': False, 'Atlas_launched': False,
              'native_tests_run': False, 'source': PIN['source'], 'phase': 'admission'}
    process = None
    started = time.monotonic()
    def save():
        temporary = records / 'build-result.tmp'
        temporary.write_text(json.dumps(result, indent=2) + '\n')
        temporary.replace(records / 'build-result.json')
    def interrupt(signum, frame):
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, signal.SIG_IGN)
        result['interrupt_signal'] = signum
        raise InterruptedError('bounded build interrupted')
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, interrupt)
    try:
        save()
        assert json.loads((records / 'restore-result.json').read_text())['status'] == 'PASS_RESTORE_ONLY'
        assert json.loads((records / 'preflight-result.json').read_text())['status'] == 'PASS_RESTORE_AND_PREFLIGHT_ONLY'
        owned = json.loads((records / 'owned-roots.json').read_text())
        assert owned['workspace'] == str(workspace) and set(owned['roots']) == {'atlas480-cargo', 'atlas480-target'}
        assert subprocess.check_output(['git', '-C', str(workspace / 'product'), 'rev-parse', 'HEAD'], text=True).strip() == PIN['source']
        assert not subprocess.check_output(['git', '-C', str(workspace / 'product'), 'status', '--porcelain', '--untracked-files=no'])
        def state_size():
            total = 0
            for root in ('atlas480-cargo', 'atlas480-target'):
                for path in (workspace / root).rglob('*'):
                    try:
                        info = path.lstat()
                    except FileNotFoundError:
                        continue  # Cargo may atomically replace an output.
                    if stat.S_ISREG(info.st_mode):
                        total += info.st_size
            return total
        initial_plain = state_size()
        growth_budget = min(PIN['limits']['max_restored_bytes'], initial_plain + 2 * 1024**3)
        checkpoint_floor = int(growth_budget * 1.02) + PIN['limits']['reserve_bytes']
        assert shutil.disk_usage(workspace).free >= checkpoint_floor + 1024**3
        result.update(initial_state_bytes=initial_plain, checkpoint_growth_budget_bytes=growth_budget,
                      checkpoint_free_floor_bytes=checkpoint_floor)
        before = digest(binary)
        env = {**os.environ, 'CARGO_HOME': str(workspace / 'atlas480-cargo'),
               'CARGO_TARGET_DIR': str(workspace / 'atlas480-target'),
               'CARGO_NET_OFFLINE': 'true', 'CARGO_BUILD_JOBS': '2', 'RUSTUP_AUTO_INSTALL': '0'}
        argv = ['cargo', '+1.95.0', 'build', '--offline', '--locked', '--release',
                '-p', 'btx-atlas', '-j2', '--message-format=json-render-diagnostics']
        result.update(phase='compile', argv=argv, original_binary_sha256=before)
        result.update(compile_may_have_started=True, process_cleanup=False)
        save()
        with (records / 'cargo-build.log').open('wb') as log:
            process = subprocess.Popen(argv, cwd=atlas, env=env, stdout=log,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            result['compile_started'] = True
            result['process_group_pid'] = process.pid
            save()
            compile_start = time.monotonic()
            progress_at = compile_start
            capacity_at = compile_start
            while process.poll() is None:
                if time.monotonic() - compile_start >= 900:
                    result['stop_reason'] = 'COMPILE_900_SECOND_LIMIT'
                    break
                if shutil.disk_usage(workspace).free < checkpoint_floor + 512 * 1024**2:
                    result['stop_reason'] = 'CHECKPOINT_HEADROOM'
                    break
                if time.monotonic() - capacity_at >= 5:
                    result['last_state_bytes'] = state_size()
                    capacity_at = time.monotonic()
                    if result['last_state_bytes'] >= growth_budget:
                        result['stop_reason'] = 'CHECKPOINT_GROWTH_BUDGET'
                        break
                if (records / 'cargo-build.log').stat().st_size > 64 * 1024**2:
                    result['stop_reason'] = 'LOG_SIZE_BOUND'
                    break
                if time.monotonic() - progress_at >= 15:
                    print(json.dumps({'phase': 'compile', 'seconds': int(time.monotonic() - compile_start),
                                      'log_bytes': (records / 'cargo-build.log').stat().st_size}), flush=True)
                    progress_at = time.monotonic()
                time.sleep(1)
            result['process_cleanup'] = stop_group(process)
            process.wait(timeout=5)
            result['cargo_exit'] = process.returncode
            result['compile_seconds'] = round(time.monotonic() - compile_start, 3)
        assert result['process_cleanup'] and not result.get('stop_reason') and result['cargo_exit'] == 0
        assert (records / 'cargo-build.log').stat().st_size <= 64 * 1024**2
        artifacts = []
        for line in (records / 'cargo-build.log').read_text(errors='replace').splitlines():
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if entry.get('reason') == 'compiler-artifact':
                artifacts.append(entry)
        app = [a for a in artifacts if a.get('target', {}).get('name') == 'btx-atlas'
               and 'bin' in a.get('target', {}).get('kind', []) and a.get('executable') == str(binary)]
        assert len(app) == 1 and app[0]['fresh'] is False
        assert binary.is_file() and not binary.is_symlink() and digest(binary) != before
        assert not subprocess.check_output(['git', '-C', str(workspace / 'product'), 'status', '--porcelain', '--untracked-files=no'])
        result['phase'] = 'ELF_metadata'
        for label, argv in [('header', ['readelf', '-h', str(binary)]),
                            ('dynamic', ['readelf', '-d', str(binary)]),
                            ('versions', ['readelf', '--version-info', str(binary)])]:
            with (records / ('atlas-elf-' + label + '.txt')).open('wb') as output:
                subprocess.run(argv, stdout=output, stderr=subprocess.STDOUT, check=True, timeout=30)
        output = Path(os.environ['RUNNER_TEMP']) / 'session3-atlas905-binary'
        output.mkdir(exist_ok=False)
        shutil.copy2(binary, output / 'btx-atlas')
        assert digest(output / 'btx-atlas') == digest(binary)
        result.update(status='PASS_ATLAS_BUILD_ONLY', phase='complete', binary_sha256=digest(binary),
                      artifact_messages=len(artifacts), fresh_artifact_messages=sum(a.get('fresh') is True for a in artifacts),
                      rebuilt_artifact_messages=sum(a.get('fresh') is False for a in artifacts),
                      loader_or_GUI_qualified=False)
    except Exception as error:
        result['status'] = 'FAIL_BUILD'
        result['error_class'] = type(error).__name__
    finally:
        if process is not None:
            result['process_cleanup'] = stop_group(process)
            if not result['process_cleanup']:
                result['status'] = 'FAIL_BUILD'
                result['stop_reason'] = 'PROCESS_CLEANUP_FAILED'
        else:
            # An interrupted Popen may not return a handle. Do not turn that
            # uncertain launch into permission to delete its possible outputs.
            result['process_cleanup'] = not result.get('compile_may_have_started', False)
        result['elapsed_seconds'] = round(time.monotonic() - started, 3)
        save()
    return 0 if result['status'] == 'PASS_ATLAS_BUILD_ONLY' else 1


if __name__ == '__main__':
    sys.exit(main())
