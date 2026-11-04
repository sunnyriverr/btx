#!/usr/bin/env python3
"""Run one fixture binary with isolated child environments and temporary files."""
import argparse, hashlib, json, os, pathlib, shutil, subprocess, tempfile, time
P = argparse.ArgumentParser()
P.add_argument('binary', type=pathlib.Path)
P.add_argument('--output', type=pathlib.Path, required=True)
P.add_argument('--native-worker', type=pathlib.Path,
               help='Real native marker executable; required on Windows')
args = P.parse_args()
binary = args.binary.resolve()
native_worker = args.native_worker.resolve() if args.native_worker else None
if os.name == 'nt' and (native_worker is None or not native_worker.is_file()):
    P.error('Windows controls require --native-worker pointing to a compiled native marker executable')
args.output.mkdir(parents=True, exist_ok=True)
base_env = {k:v for k,v in os.environ.items() if k not in
            ('BTX_OPENSSL','BTX_MODEL_INFER_CMD','BTX_LLAMA_CLI','BTX_MODEL_GENERATE','BTX_MODEL_CUDA_LOADER','BTX_EXL3_CLI','FIXTURE_MARKER')}
before_env = dict(os.environ)
worker = '''#!/bin/sh
if [ -e /dev/fd/200 ]; then exit 97; fi
printf 'invoked\\n' >> "$FIXTURE_MARKER"
case "$1" in
  -m) printf 'fixture-llama\\n';;
  --dir)
    case "$*" in
      *--max-new-tokens*) IFS= read -r request; printf '{"ok":true,"text":"fixture-adapter"}\\n';;
      *--hold*) printf '{"ok":true}\\n'; exec /bin/sleep 60;;
      *) printf '{"ok":true}\\n';;
    esac;;
  *) printf 'fixture-infer\\n';;
esac
'''
results = []
native_positive_controls = []
root = pathlib.Path(tempfile.mkdtemp(prefix='btxwc-'))
try:
    for mode in ('full', 'empty', 'override', 'infer', 'profile-nonexec', 'profile-missing'):
        work = root / mode
        work.mkdir()
        if os.name == 'nt':
            exe = work / 'worker.exe'
            shutil.copyfile(native_worker, exe)
            # Product-function fixture calls use this exact pathname; keep it a
            # real PE too, so a missing-file rejection cannot masquerade as a guard.
            shutil.copyfile(native_worker, work/'worker')
        else:
            exe = work / 'worker'; exe.write_text(worker); exe.chmod(0o700)
        (work/'nonexec').write_text('not executable'); (work/'nonexec').chmod(0o600)
        env = dict(base_env)
        backend = work/'nonexec' if mode == 'profile-nonexec' else work/'missing' if mode == 'profile-missing' else exe
        for name in ('BTX_LLAMA_CLI','BTX_MODEL_GENERATE','BTX_MODEL_CUDA_LOADER','BTX_EXL3_CLI'):
            env[name] = str(backend)
        env['FIXTURE_MARKER'] = str(work/'marker')
        if mode == 'empty': env.update(BTX_OPENSSL='', BTX_MODEL_INFER_CMD='')
        if mode == 'override': env['BTX_OPENSSL'] = 'fixture explicit openssl override'
        if mode == 'infer': env['BTX_MODEL_INFER_CMD'] = str(exe)
        if os.name == 'nt':
            setup_ok = True
            for launch_path in (exe, work/'worker'):
                t = time.monotonic()
                command = [str(launch_path)]
                try:
                    positive = subprocess.run(command, env=env, text=True,
                                              capture_output=True, timeout=10)
                    rc, stdout, stderr = positive.returncode, positive.stdout, positive.stderr
                except (OSError, subprocess.TimeoutExpired) as error:
                    rc, stdout, stderr = None, '', str(error)
                marker = work/'marker'
                invocations = marker.read_text().splitlines() if marker.exists() else []
                try:
                    output_ok = json.loads(stdout).get('ok') is True
                except (ValueError, AttributeError):
                    output_ok = False
                passed = rc == 0 and invocations == ['invoked'] and output_ok
                if marker.exists(): marker.unlink()
                cleanup_ok = not marker.exists()
                receipt = {'mode':mode, 'command':command, 'returncode':rc,
                           'seconds':round(time.monotonic()-t,3),
                           'worker_sha256':hashlib.sha256(launch_path.read_bytes()).hexdigest(),
                           'marker_invocations':invocations, 'stdout':stdout, 'stderr':stderr,
                           'marker_removed_before_guard_test':cleanup_ok,
                           'pass':passed and cleanup_ok}
                native_positive_controls.append(receipt)
                setup_ok = setup_ok and receipt['pass']
            if not setup_ok:
                results.append({'mode':mode, 'returncode':None,
                                'setup_failed':True, 'marker_invocations':[],
                                'stdout':'', 'stderr':'Native marker positive control failed; guard tests not run'})
                break
        t = time.monotonic()
        proc = subprocess.run([str(binary), mode, str(work)], env=env, text=True, capture_output=True, timeout=40)
        (args.output/f'{mode}.log').write_text(proc.stdout + proc.stderr)
        invocations = (work/'marker').read_text().splitlines() if (work/'marker').exists() else []
        result = {'mode':mode, 'returncode':proc.returncode, 'seconds':round(time.monotonic()-t,3),
                  'marker_invocations':invocations, 'stdout':proc.stdout, 'stderr':proc.stderr}
        if os.name == 'nt': result['native_no_launch'] = not invocations
        results.append(result)
finally:
    shutil.rmtree(root)
assert dict(os.environ) == before_env
summary = {'binary':str(binary), 'platform':os.name, 'temporary_root':str(root),
           'temporary_root_removed':not root.exists(), 'parent_environment_unchanged':True,
           'native_positive_controls':native_positive_controls,
           'results':results, 'pass':all(r['returncode'] == 0 and r.get('native_no_launch',True) for r in results)
                                   and all(r['pass'] for r in native_positive_controls)}
(args.output/'results.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ('results','native_positive_controls')},indent=2))
raise SystemExit(0 if summary['pass'] else 1)
