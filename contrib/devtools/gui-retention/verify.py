from pathlib import Path
import json,tarfile,subprocess,os
from checkpoint import sha,restore_timestamps,verify_restored
w=Path(os.environ['GITHUB_WORKSPACE']);a=w/'artifacts';results=[]
for case in ['success','step_failed','checkpoint_rejected']:
 co=a/('checkpoint-'+case);bo=a/('binary-'+case);record=json.loads((a/('logs-'+case)/'producer.json').read_text())
 m=json.loads((co/'manifest.json').read_text());assert sha(co/'build-state.tar.gz')==m['archive_sha256']==record['archive_sha256']
 dest=w/('restore-'+case);dest.mkdir()
 with tarfile.open(co/'build-state.tar.gz') as t:t.extractall(dest,filter='data')
 restore_timestamps(dest,m);verify_restored(dest,m)
 # Ninja cache freshness and executable round-trip after an actual artifact download.
 text=subprocess.check_output(['ninja','-C',str(dest/'gui-pilot-runtime/qtbuild'),'-n'],text=True);assert 'no work to do' in text,text
 assert subprocess.check_output([str(dest/'gui-pilot-runtime/qtbuild/fixture')],text=True)=='retention-fixture-v1\n'
 identity=json.loads((bo/'identity.json').read_text());assert sha(bo/'binary.tar.gz')==identity['tar_sha256']
 bindir=w/('binary-restore-'+case);bindir.mkdir()
 with tarfile.open(bo/'binary.tar.gz') as t:t.extractall(bindir,filter='data')
 assert sha(bindir/'fixture')==identity['sha256'];assert os.access(bindir/'fixture',os.X_OK)
 assert subprocess.check_output([str(bindir/'fixture')],text=True)==identity['output']
 if case=='checkpoint_rejected':assert 'external-link' in record['rejection'] and not (dest/'product/external-link').exists()
 results.append({'case':case,'checkpoint_roundtrip':True,'ninja_no_work':True,'independent_binary_roundtrip':True})
(w/'verification.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
