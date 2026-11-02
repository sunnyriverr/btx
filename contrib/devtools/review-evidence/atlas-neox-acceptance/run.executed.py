from pathlib import Path
import os,subprocess,json,shutil,time
r=Path(__file__).resolve().parent;py='<user-home>/.cache/uv/archive-v0/RMqQz-BbubfCVC7DuRPz5/bin/python';records=[]
def run(v,args):
 assert shutil.disk_usage(r).free>1.25*1024**3
 env=os.environ.copy();env.update(PYTHONPATH=str(r/('deps'+v)),PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HOME=str(r/'hf-offline'),TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='1')
 label='-'.join(args);start=time.monotonic()
 with (r/(label+'.log')).open('w') as f:p=subprocess.run([py,str(r/'check_model.py'),*args],env=env,stdout=f,stderr=subprocess.STDOUT,timeout=90)
 records.append({'version':v,'args':args,'returncode':p.returncode,'elapsed':time.monotonic()-start});(r/'runs.json').write_text(json.dumps(records,indent=2));print(label,p.returncode,flush=True);assert p.returncode==0,label
for v in ['457','521']:
 for tied in ['untied','tied']:run(v,['save',v+'-'+tied,tied])
for v in ['457','521']:
 for saver in ['457','521']:
  for profile in ['before','after']:run(v,['check',saver+'-untied',profile,f'{v}-{saver}-{profile}-untied'])
for profile in ['before','after']:run('521',['check','521-tied',profile,f'521-tied-{profile}'])
for kind in ['extra','missing','head']:
 run('521',['mutate','521-'+kind,kind])
 for profile in ['before','after']:run('521',['check','521-'+kind,profile,f'521-{kind}-{profile}'])
