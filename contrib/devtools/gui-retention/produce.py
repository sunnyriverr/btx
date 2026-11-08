from pathlib import Path
import os,json,subprocess,tarfile,sys,hashlib
from checkpoint import create,sha
w=Path(os.environ['GITHUB_WORKSPACE']);case=sys.argv[1];root=w/'fixture-workspace';root.mkdir();p=root/'product';p.mkdir();b=root/'gui-pilot-runtime/qtbuild';b.mkdir(parents=True);(root/'gui-pilot-runtime/openssl').mkdir()
(p/'main.c').write_text('#include <stdio.h>\nint main(void){puts("retention-fixture-v1");return 0;}\n')
(b/'build.ninja').write_text('rule compile\n  command = cc -c ../../product/main.c -o fixture.o\nrule link\n  command = cc fixture.o -o fixture\nbuild fixture.o: compile ../../product/main.c\nbuild fixture: link fixture.o\n')
subprocess.run(['ninja','-C',str(b)],check=True)
expected=sha(b/'fixture');assert subprocess.check_output([str(b/'fixture')],text=True)=='retention-fixture-v1\n'
bo=w/'binary-output';bo.mkdir()
with tarfile.open(bo/'binary.tar.gz','w:gz') as t:t.add(b/'fixture',arcname='fixture')
(bo/'identity.json').write_text(json.dumps({'sha256':expected,'output':'retention-fixture-v1\n','tar_sha256':sha(bo/'binary.tar.gz')})+'\n')
co=w/'checkpoint-output';manifest=create(root,co,{'fixture':os.environ['GITHUB_SHA'],'case':case},reserve=100*1024**2)
log=w/'retention-logs';log.mkdir();record={'case':case,'binary_ready':True,'checkpoint_ready':True,'archive_sha256':manifest['archive_sha256']}
if case=='checkpoint_rejected':
 (p/'external-link').symlink_to('/usr/bin/cc')
 try:create(root,w/'rejected-output',{'case':case},reserve=100*1024**2)
 except AssertionError as e:record['rejection']=str(e);assert 'external-link' in str(e)
 else:raise AssertionError('External link unexpectedly allowed')
 assert sha(co/'build-state.tar.gz')==manifest['archive_sha256']
(log/'producer.json').write_text(json.dumps(record,indent=2)+'\n')
raise SystemExit({'success':0,'step_failed':42,'checkpoint_rejected':43}[case])
