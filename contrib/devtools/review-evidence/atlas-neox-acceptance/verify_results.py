from pathlib import Path
import json,hashlib,subprocess,datetime,shutil
r=Path(__file__).resolve().parent
load=lambda n:json.loads((r/(n+'.json')).read_text())
for saver in ['457','521']:
 b,a=load('521-'+saver+'-before-untied'),load('521-'+saver+'-after-untied')
 assert b['status']=='REFUSED' and b['code']=='WEIGHTS' and 'lm_head.weight' in b['cause'] and 'embed_out.weight' in b['cause']
 assert a['status']=='PASS' and a['weights_equal'] and a['max_logit_delta']==0
for profile in ['before','after']:
 for key in ['457-457-'+profile+'-untied','521-tied-'+profile]:assert load(key)['status']=='PASS'
 for kind in ['extra','missing','head']:
  x=load('521-'+kind+'-'+profile);assert x['status']=='REFUSED' and x['code']=='WEIGHTS'
 x=load('457-521-'+profile+'-untied');assert x['status']=='ERROR' and 'Tokenizer class TokenizersBackend' in x['error']
assert hashlib.sha256((r/'after/contrib/atlas/neuronlab/btx_neuronlab/models.py').read_bytes()).hexdigest()=='dcfe819ce80c1f9aef299c54020a6f91265dea3b5f0ef0dbfe050d4ca1b4de93'

print("Expected before/after results and refusal controls verified.")
