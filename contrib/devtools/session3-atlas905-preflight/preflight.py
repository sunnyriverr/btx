"""Tool/dependency/source admission only: no cargo build, tests or GUI."""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tomllib

HERE = Path(__file__).resolve().parent
PIN = json.loads((HERE / 'INPUTS.json').read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    workspace = Path(os.environ['GITHUB_WORKSPACE']).resolve()
    records = Path(os.environ['RECORDS']).resolve()
    source = workspace / 'product'
    atlas = source / 'gui/atlas'
    result = {'status': 'FAIL_PREFLIGHT', 'phase': 'runtime', 'commands': [], 'build_requested': False,
              'GUI_launched': False, 'native_tests_run': False}
    try:
        assert sys.version_info[:2] == (3, 11)
        assert platform.machine() == 'x86_64' and sys.platform == 'linux'
        release = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
        assert release['ID'].strip('"') == 'ubuntu' and release['VERSION_ID'].strip('"') == '22.04'
        result['phase'] = 'restore_receipt'
        assert json.loads((records / 'restore-result.json').read_text())['status'] == 'PASS_RESTORE_ONLY'
        assert digest(records / 'restore-manifest.json') == PIN['manifest_sha256']
        manifest = json.loads((records / 'restore-manifest.json').read_text())['files']
        target_rows = {name: row for name, row in manifest.items() if name.startswith('atlas480-target/')}
        def verify_targets():
            actual = {str(p.relative_to(workspace)) for p in (workspace / 'atlas480-target').rglob('*') if p.is_file()}
            assert actual == set(target_rows)
            for name, row in target_rows.items():
                p = workspace / name
                assert not p.is_symlink() and digest(p) == row['sha256'] and p.stat().st_mtime_ns == row['mtime_ns']
        result['phase'] = 'initial_target_integrity'
        verify_targets()
        result['phase'] = 'source_inputs'
        for name, expected in PIN['source_files'].items():
            assert digest(atlas / name) == expected
        assert tomllib.loads((atlas / 'rust-toolchain.toml').read_text())['toolchain']['channel'] == PIN['toolchain']
        assert json.loads((atlas / 'src-tauri/tauri.conf.json').read_text())['build']['frontendDist'] == '../web'
        assert (atlas / 'web/index.html').is_file()
        lock = tomllib.loads((atlas / 'Cargo.lock').read_text())
        registry = [p for p in lock['package'] if p.get('source', '').startswith('registry+')]
        assert len(registry) == PIN['registry_packages'] and not any(p.get('source', '').startswith('git+') for p in lock['package'])
        result['phase'] = 'locked_crate_integrity'
        for package in registry:
            suffix = '/' + package['name'] + '-' + package['version'] + '.crate'
            names = [name for name in manifest if '/registry/cache/' in name and name.endswith(suffix)]
            assert len(names) == 1
            assert digest(workspace / names[0]) == package['checksum']
        env = {**os.environ, 'CARGO_HOME': str(workspace / 'atlas480-cargo'),
               # Metadata has no reason to touch retained compiled outputs.
               'CARGO_TARGET_DIR': str(Path(os.environ['RUNNER_TEMP']) / 'atlas905-metadata'),
               'CARGO_NET_OFFLINE': 'true', 'RUSTUP_AUTO_INSTALL': '0'}
        allowed = [
            ['git', '-C', str(source), 'rev-parse', 'HEAD'],
            ['git', '-C', str(source), 'status', '--porcelain', '--untracked-files=no'],
            ['rustc', '+1.95.0', '--version'],
            ['cargo', '+1.95.0', '--version'],
            ['pkg-config', '--modversion', 'gtk+-3.0', 'webkit2gtk-4.1', 'javascriptcoregtk-4.1', 'ayatana-appindicator3-0.1'],
            ['cargo', '+1.95.0', 'metadata', '--offline', '--locked', '--format-version', '1', '--no-deps'],
        ]
        outputs = []
        for index, argv in enumerate(allowed):
            result['phase'] = 'inspection_command_' + str(index)
            run = subprocess.run(argv, cwd=atlas, env=env, capture_output=True, text=True, timeout=60)
            result['commands'].append({'index': index, 'argv': argv, 'exit': run.returncode})
            assert run.returncode == 0
            outputs.append(run.stdout)
        assert outputs[0].strip() == PIN['source'] and not outputs[1].strip()
        assert outputs[2].startswith('rustc 1.95.0 ')
        result['phase'] = 'metadata_admission'
        metadata = json.loads(outputs[5])
        assert Path(metadata['workspace_root']) == atlas
        assert Path(metadata['target_directory']) == Path(env['CARGO_TARGET_DIR'])
        assert {p['name'] for p in metadata['packages']} == {'btx-atlas', 'btx-atlas-core'}
        result['phase'] = 'final_target_integrity'
        verify_targets()
        result.update(status='PASS_RESTORE_AND_PREFLIGHT_ONLY', phase='complete', source=PIN['source'],
                      checked_registry_crates=len(registry), target_outputs_unchanged=len(target_rows),
                      rustc_version=outputs[2].strip(), cargo_version=outputs[3].strip(),
                      pkg_config_versions=outputs[4].splitlines(),
                      incremental_compile_count=None, actual_cache_reuse_proven=False)
    except Exception as error:
        result['error_class'] = type(error).__name__
        return 1
    finally:
        (records / 'preflight-result.json').write_text(json.dumps(result, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
