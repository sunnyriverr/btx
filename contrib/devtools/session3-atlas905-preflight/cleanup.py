"""Remove exclusively recorded job-owned restore roots; combine gate receipts."""
import json
import os
from pathlib import Path
import shutil
import sys


def main():
    workspace = Path(os.environ['GITHUB_WORKSPACE']).resolve()
    records = Path(os.environ['RUNNER_TEMP']).resolve() / 'session3-atlas905-records'
    records.mkdir(exist_ok=True)
    cleanup = {'status': 'FAIL_CLEANUP', 'removed': []}
    try:
        marker = records / 'owned-roots.json'
        if marker.exists():
            assert not marker.is_symlink()
            owned = json.loads(marker.read_text())
            assert owned['workspace'] == str(workspace) and owned['artifact'] == 13743770446
            assert len(owned['roots']) == len(set(owned['roots']))
            for name in owned['roots']:
                assert name in {'atlas480-cargo', 'atlas480-target'}
                target = workspace / name
                assert target.parent == workspace and not target.is_symlink()
                if target.exists():
                    shutil.rmtree(target)
                assert not target.exists()
                cleanup['removed'].append(name)
        cleanup['status'] = 'PASS_CLEANUP_OWNED_ROOTS_ONLY'
    except Exception as error:
        cleanup['error_class'] = type(error).__name__
    finally:
        (records / 'cleanup-result.json').write_text(json.dumps(cleanup, indent=2) + '\n')
    overall = {'status': 'NOT_QUALIFIED', 'scope': 'restore and preflight only; no build or GUI'}
    try:
        restore = json.loads((records / 'restore-result.json').read_text())
        preflight = json.loads((records / 'preflight-result.json').read_text())
        if (restore['status'] == 'PASS_RESTORE_ONLY'
                and preflight['status'] == 'PASS_RESTORE_AND_PREFLIGHT_ONLY'
                and cleanup['status'] == 'PASS_CLEANUP_OWNED_ROOTS_ONLY'
                and set(cleanup['removed']) == {'atlas480-cargo', 'atlas480-target'}):
            overall['status'] = 'PASS_RESTORE_PREFLIGHT_CLEANUP_ONLY'
    except (OSError, ValueError, KeyError):
        pass
    (records / 'qualification-result.json').write_text(json.dumps(overall, indent=2) + '\n')
    return 0 if cleanup['status'] == 'PASS_CLEANUP_OWNED_ROOTS_ONLY' else 1


if __name__ == '__main__':
    sys.exit(main())
