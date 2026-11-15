from pathlib import Path
import sys,tarfile,ast
root=Path(sys.argv[1]);out=Path('records');out.mkdir(exist_ok=True)
for p in root.rglob('*.log'):
 text=p.read_text(errors='replace').replace('btx_minio_access_sentinel','TEST_REDACTED').replace('btx_minio_secret_sentinel','TEST_REDACTED')
 # Test credential labels may differ across fixtures; redact actual sentinel values.
 tree=ast.parse(Path(__file__).with_name('base_minio.py').read_text())
 values={target.id:ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign) for target in node.targets if isinstance(target,ast.Name) and target.id in ('ACCESS_SENTINEL','SECRET_SENTINEL')}
 ACCESS_SENTINEL=values['ACCESS_SENTINEL'];SECRET_SENTINEL=values['SECRET_SENTINEL']
 text=text.replace(ACCESS_SENTINEL,'TEST_REDACTED').replace(SECRET_SENTINEL,'TEST_REDACTED')
 name='scratch-'+str(p.relative_to(root)).replace('/','__');(out/name).write_text(text)
if (root/'preserved').exists():
 with tarfile.open(out/'preserved-fixture.tar.gz','w:gz') as t:t.add(root/'preserved',arcname='preserved')
