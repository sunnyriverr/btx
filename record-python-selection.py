"""Future bounded interpreter-selection evidence; not an archive admission gate.

Run only inside the separately authorized packaging-only controller. This file
has been prepared by source review only; no native Python probe ran at drafting.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

WORKSPACE = Path('/home/runner/work/btx/btx')
PREFIX = Path('/opt/hostedtoolcache/Python/3.12.16/x64')
ORIGINAL = '018d8dcbb0bfec2c36e62397b80dcad884b67422e0328409d189ba6cfb5aa2d4'
CANDIDATE = '721fa1f54b51223cde80a1c85c4b8c996da916c5dab2fd7ff4fc17a8be72eab7'
PATCH = '9ad1291bf4924465066c0f9ad11d06d823feaa6147a1f08a6c26859bc4795140'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def load(name, path, digest):
    require(path.is_file() and not path.is_symlink() and sha(path) == digest,
            'Pinned selector input bytes: ' + name)
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, 'Selector module loader')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write(path, row):
    data = json.dumps(row, indent=2, sort_keys=True) + '\n'
    require(len(data.encode()) <= 8 * 1024**2, 'Selection record bound')
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(data)
    tmp.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--python', required=True)
    args = parser.parse_args()
    w = Path(args.workspace).resolve()
    require(w == WORKSPACE, 'Exact isolated workspace')
    python = Path(args.python)
    require(python.is_absolute() and python.is_file()
            and python == PREFIX / 'bin/python3'
            and Path(sys.executable).resolve() == python.resolve(),
            'Exact selected Python3.12 interpreter')
    original_path = w / 'product/scripts/release/bundle_python_runtime.py'
    candidate_path = w / 'package-overlay/scripts/release/bundle_python_runtime.py'
    patch_path = w / 'control/patch/nested-site-packages.patch'
    require(patch_path.is_file() and not patch_path.is_symlink() and sha(patch_path) == PATCH,
            'Reviewed patch bytes')
    records = w / 'build-records'
    require(records.is_dir() and not records.is_symlink(), 'Owned records directory')
    destination = records / 'python-selection.json'
    require(not destination.exists(), 'Refuse stale selection result')
    result = {'status': 'DIAGNOSTIC_INCOMPLETE',
              'scope': 'Host interpreter module/copy selection only; not staged imports or archive admission',
              'original_module_sha256': ORIGINAL, 'candidate_module_sha256': CANDIDATE,
              'reviewed_patch_sha256': PATCH, 'python': str(python),
              'probe_invocations': 0, 'shipping_gate_override': False}
    try:
        original = load('original_python_bundle_selection', original_path, ORIGINAL)
        candidate = load('candidate_python_bundle_selection', candidate_path, CANDIDATE)
        modules = candidate.swapnet_imports(w / 'product')
        require(modules and len(modules) <= 1000
                and any(name.startswith('cryptography.') for name in modules),
                'Frozen source import list must exercise cryptography')
        result['required_imports'] = modules
        # Exactly one original maintained isolated interpreter probe supplies
        # the same module map to both pure selection implementations.
        result['probe_invocations'] = 1
        info = candidate.probe_interpreter(str(python), modules)
        result['interpreter_probe'] = info
        require(info['version'] == '3.12' and Path(info['prefix']) == PREFIX
                and Path(info['stdlib']) == PREFIX / 'lib/python3.12',
                'Expected selected interpreter layout')
        require(not info['failed'], 'Build-host required imports failed')
        require(isinstance(info['modules'], dict) and len(info['modules']) <= 5000,
                'Interpreter module inventory bound')
        before = original._third_party_roots(info)
        after = candidate._third_party_roots(info)
        result['original_third_party_roots'] = {name: str(path) for name, path in before.items()}
        result['candidate_third_party_roots'] = {name: str(path) for name, path in after.items()}
        crypto_file = info['modules'].get('cryptography')
        require(crypto_file is not None, 'Actual cryptography file path absent')
        result['cryptography_module_file'] = crypto_file
        nested = Path(info['stdlib']) / 'site-packages'
        require(Path(crypto_file).is_relative_to(nested),
                'Actual cryptography module must exercise direct nested site-packages')
        require('cryptography' not in before and 'cryptography' in after,
                'Intended missing-root selection delta absent')
        require(after['cryptography'] == nested / 'cryptography',
                'Candidate cryptography package root differs')
        result['status'] = 'EXPECTED_NESTED_SELECTION_DELTA'
        write(destination, result)
        print(json.dumps({'status': result['status'],
                          'required_imports': len(modules),
                          'probe_invocations': result['probe_invocations'],
                          'original_includes_cryptography': 'cryptography' in before,
                          'candidate_includes_cryptography': 'cryptography' in after}))
        return 0
    except BaseException as error:
        result['status'] = 'SELECTION_DIAGNOSTIC_FAILED'
        result['error'] = repr(error)
        write(destination, result)
        raise


if __name__ == '__main__':
    sys.exit(main())
