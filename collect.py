from pathlib import Path
import sys,tarfile
root=Path(sys.argv[1]);out=Path('records');out.mkdir(exist_ok=True)
for p in root.rglob('*.log'):
 text=p.read_text(errors='replace').replace('btx_minio_access_sentinel','TEST_REDACTED').replace('btx_minio_secret_sentinel','TEST_REDACTED')
 # Test credential labels may differ across fixtures; redact actual sentinel values.
 from base_minio import ACCESS_SENTINEL,SECRET_SENTINEL
 text=text.replace(ACCESS_SENTINEL,'TEST_REDACTED').replace(SECRET_SENTINEL,'TEST_REDACTED')
 name='scratch-'+str(p.relative_to(root)).replace('/','__');(out/name).write_text(text)
if (root/'preserved').exists():
 with tarfile.open(out/'preserved-fixture.tar.gz','w:gz') as t:t.add(root/'preserved',arcname='preserved')
