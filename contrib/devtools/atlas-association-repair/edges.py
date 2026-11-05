"""Run the maintained native regression against vendor and repaired macros."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
HERE=Path(__file__).resolve().parent;OUT=Path('atlas-installer-results').resolve()
compiler=Path(os.environ['LOCALAPPDATA'])/'tauri/NSIS/makensis.exe'
test=Path('atlas-product/gui/atlas/tests/nsis_associations.py').resolve()
records=[]
for name,extra in [('before',['--baseline-macros',str(HERE/'original-FileAssociation.nsh')]),('after',[])]:
 output=OUT/('edge-'+name+'.json');args=[sys.executable,str(test),'--makensis',str(compiler),'--out',str(output),*extra]
 r=subprocess.run(args,capture_output=True,timeout=180);(OUT/('edge-'+name+'.log')).write_bytes(r.stdout+b'\nSTDERR\n'+r.stderr)
 data=json.loads(output.read_text());assert not data['errors'],data['errors'];assert data['cleanup']['scratch_removed']
 assert len({x['case'] for x in data['checks']})==8
 if name=='before':
  assert r.returncode==1 and not data['pass']
  for case in ['repeated','later']:assert any(x['case']==case and x['check']=='restores selected handler' and not x['pass'] for x in data['checks'])
 else:assert r.returncode==0 and data['pass'] and all(x['pass'] for x in data['checks'])
 records.append({'variant':name,'returncode':r.returncode,'pass':data['pass'],'case_count':8,'checks':len(data['checks']),'failures':[x for x in data['checks'] if not x['pass']]})
(OUT/'edge-comparison.json').write_text(json.dumps({'test_sha256':hashlib.sha256(test.read_bytes()).hexdigest(),'records':records,'pass':True},indent=2)+'\n');print(json.dumps(records,indent=2))
