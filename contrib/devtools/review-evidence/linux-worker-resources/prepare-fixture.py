from pathlib import Path
import sys,json,hashlib,shutil
here=Path(__file__).resolve().parent
repo=here.parents[3]
target=Path(sys.argv[1]).resolve()
assert not target.exists(), "Choose a new fixture directory"
manifest=json.loads((here/'manifest.json').read_text())
for name,expected in manifest['files'].items():
    data=(repo/name).read_bytes()
    assert hashlib.sha256(data).hexdigest()==expected, name
    path=target/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
for name in ['manifest.json','build.py','probe.c','guest-run.py']:
    shutil.copy2(here/name,target/name)
print(target)
