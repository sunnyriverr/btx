import json,subprocess,os,shutil
from pathlib import Path
P=Path(__file__).resolve().parents[1];S=P/'repair/source';V=P/'python-pkg/Python_Framework.pkg/Payload/Versions/3.12';env=dict(os.environ);env.update(DYLD_FRAMEWORK_PATH=str(P/'control-frameworks'),DYLD_LIBRARY_PATH=str(V/'lib'),HOME=str(P/'repair/packaging-home'),PYTHONDONTWRITEBYTECODE='1');Path(env['HOME']).mkdir(exist_ok=True)
for kind in (['candidate'] if os.environ.get('ONLY_CANDIDATE') else ['baseline','candidate']):
 out=P/'repair'/kind/'archives';out.mkdir(parents=True,exist_ok=True);script=P/'repair/baseline/scripts/release/package_release_archive.py' if kind=='baseline' else S/'scripts/release/package_release_archive.py'
 cmd=[str(Path('work/btx-lanes/session-3/swapnet-maker-terminal-capacity/venv/bin/python').resolve()),str(script),'--output-dir',str(out),'--version','0.34.16','--platform-id','macos-arm64','--btxd',str(P/'repair/packaging-input/btxd'),'--btx-cli',str(P/'repair/packaging-input/btx-cli'),'--btx-util',str(P/'repair/packaging-input/btx-util'),'--source-root',str(S),'--python',str(V/'bin/python3.12')]
 print(kind,'packing',flush=True)
 with (P/'repair'/f'{kind}-pack.stdout').open('w') as stdout,(P/'repair'/f'{kind}-pack.stderr').open('w') as stderr:r=subprocess.run(cmd,env=env,stdout=stdout,stderr=stderr,timeout=240)
 print(kind,r.returncode,flush=True)
 if r.returncode:print((P/'repair'/f'{kind}-pack.stderr').read_text()[-3500:]);raise SystemExit(r.returncode)
 print((P/'repair'/f'{kind}-pack.stdout').read_text()[:200],flush=True)
