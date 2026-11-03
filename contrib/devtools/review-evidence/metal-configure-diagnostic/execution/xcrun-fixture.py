#!/usr/bin/env python3
"""Recording protocol fixture: never a real Metal compiler or GPU qualification."""
import json, os, pathlib, sys
args = sys.argv[1:]
with open(os.environ['BTX_FIXTURE_LOG'], 'a') as log:
    log.write(json.dumps(args)+'\n')
assert args[:2] == ['-sdk', 'macosx'], args
assert os.environ['BTX_FIXTURE_MODE'] != 'reject', 'unexpected gated invocation'
if args[2] == 'metal':
    if '-std=metal4.0' in args:
        print('fixture: Metal 4 unsupported', file=sys.stderr)
        sys.exit(1)
    assert args[3] == '-c' and '-std=metal4.0' not in args
    source = pathlib.Path(args[4])
    assert 'kernel void btx_metal4_probe' in source.read_text()
    pathlib.Path(args[args.index('-o')+1]).write_text('fixture AIR\n')
elif args[2] == 'metallib':
    assert pathlib.Path(args[3]).read_text() == 'fixture AIR\n'
    if os.environ['BTX_FIXTURE_MODE'] == 'missing-link':
        print('fixture: metallib unavailable', file=sys.stderr)
        sys.exit(72)
    pathlib.Path(args[args.index('-o')+1]).write_text('fixture metallib\n')
else:
    raise AssertionError(args)
