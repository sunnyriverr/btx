"""Run owned cleanup and combine build/checkpoint receipts without relaunching."""
import json
import os
from pathlib import Path
import sys
import cleanup


def main():
    records = Path(os.environ['RUNNER_TEMP']).resolve() / 'session3-atlas905-records'
    records.mkdir(exist_ok=True)
    build_path = records / 'build-result.json'
    try:
        build = json.loads(build_path.read_text()) if build_path.exists() else {}
        safe_cleanup = not build.get('compile_may_have_started') or build.get('process_cleanup') is True
    except (OSError, ValueError):
        safe_cleanup = False
    if safe_cleanup:
        code = cleanup.main()
    else:
        # Do not delete retained state under a compiler that may still be live.
        code = 1
        (records / 'cleanup-result.json').write_text(json.dumps({
            'status': 'FAIL_CLEANUP_COMPILER_STATE_UNPROVEN', 'removed': []}) + '\n')
    result = {'status': 'NOT_QUALIFIED', 'scope': 'Atlas-only build and checkpoint; no tests, loader run or GUI'}
    try:
        build = json.loads((records / 'build-result.json').read_text())
        state = json.loads((records / 'checkpoint-result.json').read_text())
        prior = json.loads((records / 'qualification-result.json').read_text())
        if (code == 0 and prior['status'] == 'PASS_RESTORE_PREFLIGHT_CLEANUP_ONLY'
                and build['status'] == 'PASS_ATLAS_BUILD_ONLY'
                and build['process_cleanup'] is True
                and state['status'] == 'PASS_CHECKPOINT_RETAINED_NOT_RESTORED'):
            result.update(status='PASS_ATLAS_BUILD_AND_CHECKPOINT_ONLY',
                          binary_sha256=build['binary_sha256'], checkpoint_sha256=state['archive_sha256'])
    except (OSError, ValueError, KeyError):
        pass
    (records / 'build-qualification-result.json').write_text(json.dumps(result, indent=2) + '\n')
    return 0 if code == 0 and result['status'] == 'PASS_ATLAS_BUILD_AND_CHECKPOINT_ONLY' else 1


if __name__ == '__main__':
    sys.exit(main())
