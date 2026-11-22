"""Controlled read-only worker transport for native presentation acceptance."""
import argparse
import json
from pathlib import Path
import sys

# Match the installed worker's isolated-import pattern, without scientific deps.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixture_data import MODEL, PROFILE, PROFILE_ID, SUMMARY


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--store', required=True, type=Path)
    parser.add_argument('--stream', action='store_true')
    args = parser.parse_args()
    args.store.mkdir(parents=True, exist_ok=True)
    raw = sys.stdin.buffer.readline(262145)
    assert len(raw) <= 262144 and raw.endswith(b'\n')
    request = json.loads(raw)
    action = request['action']
    payload = request['payload']
    allowed = action in {'status', 'models', 'list', 'profile'}
    with (args.store / 'fixture-calls.jsonl').open('a') as stream:
        stream.write(json.dumps({'action': action, 'operation_id': request['operation_id'],
                                 'allowed': allowed}) + '\n')
    if not allowed:
        print(json.dumps({'ok': False, 'error': {'code': 'FIXTURE_MUTATION_REFUSED',
                                                'message': 'Controlled fixture accepts reads only'}}))
        return 2
    if action == 'status':
        result = {'crypto': 'CONTROLLED_GUI_FIXTURE_NOT_SCIENTIFIC', 'publisher': None}
    elif action == 'models':
        result = {'items': [MODEL]}
    elif action == 'list':
        result = {'items': [SUMMARY]}
    else:
        assert payload['profile_id'] == PROFILE_ID
        result = PROFILE
    print(json.dumps({'ok': True, 'result': result}), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
