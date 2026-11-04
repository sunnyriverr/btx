"""Native exact-function controls; no whole-node qualification inferred."""
from pathlib import Path
import sys, subprocess, hashlib, json, time

P = Path(__file__).resolve().parent
source, root, evidence = map(Path, sys.argv[1:])
records = []
for compiler in ['cl', 'clang-cl']:
    output = root / ('controls-' + compiler)
    output.mkdir(exist_ok=True)
    exe = output / 'controls.exe'
    worker = output / 'native-worker.exe'
    worker_command = [compiler, '/nologo', '/std:c++20', '/EHsc', '/O2', '/MT', str(P / 'native-worker.cpp'), '/Fe' + str(worker), '/Fo' + str(output / 'native-worker.obj')]
    built = subprocess.run(worker_command, cwd=output, capture_output=True, timeout=60)
    (evidence / (compiler + '-native-worker-build.log')).write_bytes(built.stdout + built.stderr)
    if built.returncode:
        raise SystemExit(built.returncode)
    unit = P / 'candidate-controls.cpp'
    uv = source / 'src/univalue/lib'
    command = [compiler, '/nologo', '/std:c++20', '/EHsc', '/O2', '/MT', '/DWIN32', '/DNOMINMAX', '/D_CRT_SECURE_NO_WARNINGS']
    command += ['/I' + str(p) for p in [P, source / 'src', source / 'src/univalue/include']]
    command += [str(unit)] + [str(uv / n) for n in ['univalue.cpp', 'univalue_get.cpp', 'univalue_read.cpp', 'univalue_write.cpp']]
    command += ['/Fe' + str(exe), '/Fo' + str(output) + '\\']
    start = time.monotonic()
    result = subprocess.run(command, cwd=output, capture_output=True, timeout=150)
    log = evidence / (compiler + '-controls-build.log')
    log.write_bytes(result.stdout + result.stderr)
    row = {'compiler': compiler, 'command': command, 'build_exit': result.returncode, 'seconds': round(time.monotonic() - start, 2), 'build_log_sha256': hashlib.sha256(log.read_bytes()).hexdigest()}
    records.append(row)
    row['worker_command'] = worker_command
    row['worker_binary_sha256'] = hashlib.sha256(worker.read_bytes()).hexdigest()
    if result.returncode:
        (evidence / 'native-controls.json').write_text(json.dumps(records, indent=2) + '\n')
        raise SystemExit(result.returncode)
    row['binary_sha256'] = hashlib.sha256(exe.read_bytes()).hexdigest()
    run = subprocess.run([sys.executable, str(P / 'run.py'), str(exe), '--native-worker', str(worker), '--output', str(evidence / (compiler + '-controls'))], capture_output=True, timeout=150)
    (evidence / (compiler + '-controls-run.log')).write_bytes(run.stdout + run.stderr)
    row['run_exit'] = run.returncode
    row['results'] = json.loads((evidence / (compiler + '-controls/results.json')).read_text())
    (evidence / 'native-controls.json').write_text(json.dumps(records, indent=2) + '\n')
    if run.returncode or not row['results']['pass']:
        raise SystemExit(1)
    exe.unlink()
    worker.unlink()
    for obj in output.glob('*.obj'):
        obj.unlink()
print('Both native compilers passed the exact-function control fixture')
