"""Clean only the fixture-owned binary; never approve a dialog or run an app."""
import json
import os
from pathlib import Path
import shutil
import sys


def main():
    root = Path(os.environ['RUNNER_TEMP']).resolve()
    records = root / 'session3-atlas905-dialog-records'
    records.mkdir(exist_ok=True)
    result = {'status': 'NOT_QUALIFIED', 'visual_review': 'REQUIRED_NOT_PERFORMED'}
    cleanup = {'status': 'FAIL_CLEANUP', 'binary_removed': False}
    try:
        driver_path = records / 'dialog-result.json'
        driver = json.loads(driver_path.read_text()) if driver_path.exists() else {}
        if driver.get('launch_intent') and driver.get('process_group_cleanup') is not True:
            raise RuntimeError('Atlas cleanup unproven')
        marker = records / 'binary-owned.json'
        if marker.exists():
            path = Path(json.loads(marker.read_text())['path'])
            assert path == root / 'session3-atlas905-dialog-binary' and not path.is_symlink()
            if path.exists():
                shutil.rmtree(path)
            cleanup['binary_removed'] = not path.exists()
        for name in ('session3-atlas905-dialog-xdg', 'session3-atlas905-dialog-portal'):
            path = root / name
            assert not path.is_symlink()
            if path.exists():
                shutil.rmtree(path)
            cleanup[name + '_removed'] = not path.exists()
        cleanup['status'] = 'PASS_OWNED_CLEANUP'
        if (driver.get('status') == 'PASS_AUTOMATED_DIALOG_CANCEL_PENDING_VISUAL_REVIEW'
                and driver.get('process_group_cleanup') is True and driver.get('scratch_removed') is True
                and cleanup['binary_removed']):
            result.update(status='PASS_AUTOMATED_CANCEL_PENDING_VISUAL_REVIEW',
                          source=driver['source'], binary_sha256=driver['binary_sha256'],
                          signatures_or_science_qualified=False, no_rebuild=True)
    except Exception as error:
        cleanup['error_class'] = type(error).__name__
    (records / 'cleanup-result.json').write_text(json.dumps(cleanup, indent=2) + '\n')
    (records / 'qualification-result.json').write_text(json.dumps(result, indent=2) + '\n')
    return 0 if result['status'] == 'PASS_AUTOMATED_CANCEL_PENDING_VISUAL_REVIEW' else 1


if __name__ == '__main__':
    sys.exit(main())
