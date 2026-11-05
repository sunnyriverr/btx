"""Native unchanged-NSIS-macro observations; never modifies real associations."""
from pathlib import Path
import hashlib, json, os, platform, shutil, subprocess, sys, time, urllib.request, uuid, zipfile

HERE = Path(__file__).resolve().parent
OUT = Path('association-results').resolve()
OUT.mkdir(exist_ok=True)
STATE = {'schema': 1, 'platform': platform.platform(), 'python': sys.version,
         'scope': 'unchanged NSIS association macros; synthetic keys; no Atlas bundle or shell opening',
         'controls': [], 'restoration_checks': [], 'snapshots': [], 'commands': [], 'errors': []}

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def check(name, okay, category='controls', **data):
    STATE[category].append({'name': name, 'pass': bool(okay), **data})
    if category == 'controls' and not okay: raise RuntimeError(name)

def command(args, log, timeout=60, env=None):
    start = time.monotonic()
    result = subprocess.run([str(x) for x in args], capture_output=True, timeout=timeout, env=env)
    (OUT / log).write_bytes(result.stdout + b'\nSTDERR\n' + result.stderr)
    STATE['commands'].append({'args': list(map(str, args)), 'exit': result.returncode,
                              'seconds': round(time.monotonic()-start, 3), 'log': log})
    check(log + ' exit', result.returncode == 0)
    return result

def main():
    import winreg as reg
    check('native Windows', sys.platform == 'win32')
    manifest = json.loads((HERE / 'inputs.json').read_text())
    STATE['inputs'] = manifest
    for name, digest in manifest['files'].items(): check('input bytes ' + name, sha(HERE/name) == digest)
    token = uuid.uuid4().hex
    STATE['fixture_token'] = token
    scratch = Path(os.environ['RUNNER_TEMP']) / ('btx-assoc-' + token)
    scratch.mkdir()
    STATE['scratch'] = str(scratch)
    owned_keys = []
    view = reg.KEY_WOW64_64KEY
    def path(name): return 'Software\\Classes\\' + name
    def exists(key):
        try:
            with reg.OpenKey(reg.HKEY_CURRENT_USER, key, 0, reg.KEY_READ | view): return True
        except FileNotFoundError: return False
    def tree(key):
        try: handle = reg.OpenKey(reg.HKEY_CURRENT_USER, key, 0, reg.KEY_READ | view)
        except FileNotFoundError: return None
        with handle:
            values = {}; children = {}
            for i in range(reg.QueryInfoKey(handle)[1]):
                name, value, kind = reg.EnumValue(handle, i)
                values[name] = {'type': kind, 'value': value}
            for i in range(reg.QueryInfoKey(handle)[0]):
                name = reg.EnumKey(handle, i); children[name] = tree(key + '\\' + name)
            return {'values': values, 'children': children}
    def write(key, name, value, kind=reg.REG_SZ):
        with reg.CreateKeyEx(reg.HKEY_CURRENT_USER, key, 0, reg.KEY_WRITE | view) as h:
            reg.SetValueEx(h, name, 0, kind, value)
    def default(key):
        state = tree(key)
        return None if state is None else state['values'].get('', {}).get('value')
    def remove(key):
        if not exists(key): return
        with reg.OpenKey(reg.HKEY_CURRENT_USER, key, 0, reg.KEY_READ | view) as h:
            children = [reg.EnumKey(h,i) for i in range(reg.QueryInfoKey(h)[0])]
        for child in children: remove(key+'\\'+child)
        reg.DeleteKeyEx(reg.HKEY_CURRENT_USER, key, view, 0)
    def snap(case, stage, keys):
        STATE['snapshots'].append({'case': case, 'stage': stage,
                                   'keys': {key: tree(key) for key in keys}})
    def wait_for(predicate, label, seconds=10):
        until = time.monotonic() + seconds
        while not predicate() and time.monotonic() < until: time.sleep(.05)
        check(label, predicate())
    try:
        asset = manifest['nsis']
        archive = scratch/'nsis.zip'
        with urllib.request.urlopen(asset['url'], timeout=60) as response: archive.write_bytes(response.read())
        check('NSIS archive digest', sha(archive) == asset['sha256'])
        with zipfile.ZipFile(archive) as z:
            check('bounded compiler archive', sum(x.file_size for x in z.infolist()) < 50_000_000)
            check('compiler archive paths', all(not Path(x.filename).is_absolute() and '..' not in Path(x.filename).parts for x in z.infolist()))
            z.extractall(scratch/'tool')
        # Match Tauri's <toolset>/makensis.exe launcher, not Bin/makensis.exe.
        compiler = scratch/'tool/nsis-3.13/makensis.exe'
        check('Tauri compiler launcher exists', compiler.is_file())
        for relative, digest in manifest['compiler_files'].items():
            check('compiler file '+relative, sha(scratch/'tool'/relative) == digest)
        STATE['compiler'] = {'sha256': sha(compiler), 'path': str(compiler), 'files': manifest['compiler_files']}
        command([compiler, '/VERSION'], 'compiler-version.log')
        sentinel = path('BTXProbe.'+token+'.Unrelated')
        check('sentinel absent', not exists(sentinel))
        owned_keys.append(sentinel)
        write(sentinel, 'preserve', 'unrelated-'+token)
        write(sentinel, 'numeric', 713, reg.REG_DWORD)
        sentinel_before = tree(sentinel)
        for case in ['clean', 'prior', 'reinstall', 'later', 'reuse']:
            ext = 'btxprobe'+token+case
            prog = 'BTXProbe.'+token+'.'+case
            previous = prog+'.Previous'; later = prog+'.Later'
            keys = [path('.'+ext), path(prog), path(previous), path(later)]
            check(case+' fixture keys absent', all(not exists(key) for key in keys))
            owned_keys.extend(keys)
            case_dir = scratch/case; case_dir.mkdir()
            uninstall_temp = case_dir/'uninstall-temp'; uninstall_temp.mkdir()
            destination = case_dir/'installed'; completion = case_dir/'complete.txt'
            installer = case_dir/'install.exe'
            command([compiler, '/V3', '/INPUTCHARSET', 'UTF8', '/DOUTPUT='+str(installer),
                     '/DDESTINATION='+str(destination), '/DCOMPLETION='+str(completion),
                     '/DEXTENSION='+ext, '/DFILECLASS='+prog, HERE/'fixture.nsi'], case+'-compile.log')
            STATE.setdefault('binaries', {})[case] = {'installer': sha(installer)}
            if case != 'clean':
                write(path(previous), '', 'Previous fixture handler')
                write(path(previous)+'\\shell\\open\\command', '', '"'+sys.executable+'" "previous-fixture-only" "%1"')
                write(path('.'+ext), '', previous)
                write(path('.'+ext), 'unrelated', 'keep-'+token)
                write(path('.'+ext)+'\\UnrelatedSubkey', 'number', 991, reg.REG_DWORD)
            previous_tree = tree(path(previous))
            snap(case, 'before', keys)
            def install(label):
                command([installer, '/S'], case+'-'+label+'.log')
                check(case+' registered '+label, default(path('.'+ext)) == prog)
                check(case+' handler present '+label, exists(path(prog)+'\\shell\\open\\command'))
                check(case+' uninstaller exists '+label, (destination/'uninstall.exe').is_file())
                STATE['binaries'][case]['uninstaller-'+label] = sha(destination/'uninstall.exe')
                snap(case, label, keys)
            def uninstall(label):
                completion.unlink(missing_ok=True)
                # Default NSIS self-copy: launcher exit alone is not completion.
                environment = dict(os.environ, TEMP=str(uninstall_temp), TMP=str(uninstall_temp))
                command([destination/'uninstall.exe', '/S'], case+'-'+label+'.log', env=environment)
                def completed():
                    try: return completion.read_text() == 'association-uninstall-finished'
                    except OSError: return False
                wait_for(completed, case+' completion marker finished '+label)
                check(case+' completion '+label, completion.read_text() == 'association-uninstall-finished')
                check(case+' handler removed '+label, not exists(path(prog)))
                check(case+' install directory removed '+label, not destination.exists())
                snap(case, label, keys)
            install('install1')
            if case == 'reinstall': install('install2')
            if case == 'later':
                write(path(later), '', 'Later fixture handler')
                write(path(later)+'\\shell\\open\\command', '', '"'+sys.executable+'" "later-fixture-only" "%1"')
                write(path('.'+ext), '', later)
                later_tree = tree(path(later))
                snap(case, 'later-choice', keys)
            uninstall('uninstall1')
            expected = '' if case == 'clean' else (later if case == 'later' else previous)
            actual = default(path('.'+ext))
            check(case+' default retains string type', tree(path('.'+ext))['values']['']['type'] == reg.REG_SZ)
            check(case+' default restored', actual == expected, 'restoration_checks', expected=expected, actual=actual,
                  points_to_removed_fixture=(actual == prog and not exists(path(prog))))
            if case == 'reuse':
                install('install-cycle2'); uninstall('uninstall-cycle2')
                check(case+' second cycle restores prior', default(path('.'+ext)) == previous, 'restoration_checks')
            check(case+' prior handler unchanged', tree(path(previous)) == previous_tree)
            if case == 'later': check('later handler definition unchanged', tree(path(later)) == later_tree)
            if case != 'clean':
                ext_tree = tree(path('.'+ext))
                check(case+' unrelated value preserved', ext_tree['values']['unrelated'] == {'type': reg.REG_SZ, 'value': 'keep-'+token})
                check(case+' unrelated subkey preserved', ext_tree['children']['UnrelatedSubkey']['values']['number'] == {'type': reg.REG_DWORD, 'value': 991})
            check(case+' separate sentinel unchanged', tree(sentinel) == sentinel_before)
        STATE['uninstaller_mode'] = 'Native generated uninstaller /S with default self-copy into fixture TEMP/TMP; launcher exit plus final completion marker and directory removal checked. Not full Tauri template execution.'
    finally:
        for key in reversed(owned_keys): remove(key)
        check('fixture registry cleanup', all(not exists(key) for key in owned_keys))
        until = time.monotonic() + 10
        while scratch.exists():
            try: shutil.rmtree(scratch)
            except OSError:
                if time.monotonic() >= until: raise
                time.sleep(.1)
        check('fixture filesystem cleanup', not scratch.exists())

try:
    main()
except Exception as exc:
    STATE['errors'].append(repr(exc))
finally:
    STATE['controls_pass'] = bool(STATE['controls']) and all(x['pass'] for x in STATE['controls']) and not STATE['errors']
    STATE['restoration_pass'] = bool(STATE['restoration_checks']) and all(x['pass'] for x in STATE['restoration_checks'])
    STATE['restoration_failures'] = [x for x in STATE['restoration_checks'] if not x['pass']]
    (OUT/'result.json').write_text(json.dumps(STATE,indent=2)+'\n')
    print(json.dumps({k:STATE[k] for k in ['controls_pass','restoration_pass','restoration_failures','errors']},indent=2))
sys.exit(0 if STATE['controls_pass'] and STATE['restoration_pass'] else 1)
