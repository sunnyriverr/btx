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
identities={}
repo=r.parent.parent/'btx-atlas-test2/source'
for profile,commit in [('before','6d0fbf6ba492b16bdef64ade30d85ea8dffd287a'),('after','acbf7efb20b1b82da06affdae2ead08068cf743c')]:
 files={};root=r/profile/'contrib/atlas/neuronlab'
 for p in root.rglob('*'):
  if p.is_file():
   relative=p.relative_to(r/profile).as_posix();blob=subprocess.check_output(['git','-C',str(repo),'show',commit+':'+relative]);assert blob==p.read_bytes();files[relative]=hashlib.sha256(blob).hexdigest()
 identities[profile]={'commit':commit,'files':files}
(r/'source-identities.json').write_text(json.dumps(identities,indent=2)+'\n')
summary={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'requested_actual_transformers_acceptance_passed_private','head':identities['after']['commit'],'before':identities['before']['commit'],'platform':subprocess.check_output(['sw_vers'],text=True),'architecture':'arm64 Apple M4','device':'CPU, one torch thread','torch':'2.14.1 (JPP original used2.10.0)','transformers':['4.57.6','5.21.1'],'requested_cases':'5.21.1 loads untied checkpoints saved unmodified by each version: beforeWEIGHTS2/2, afterPASS2/2','controls':'4.57.6 same-version load PASSboth;5.21.1tiedPASSboth;extra/secondmissing/headmissingWEIGHTSboth','weights_logits':'all successful loads match plain transformers loaded same fixture; exact state tensors and max logit delta0','reverse_version_limit':'5.21.1-save→4.57.6load fails both at AutoTokenizer TokenizersBackend, before changed weight code','runs_per_case':1,'network':'packages installed from package index into isolated targets; no model/config/tokenizer downloaded; checkpoint tests offline','source_modified':False,'free_disk_bytes':shutil.disk_usage(r).free,'next':'one scoped item5 evidence handoff on273whenauthorized; no product patch/newPR/extra matrix','published':False}
(r/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
for v in ['457','521']:(r/('versions'+v+'.json')).write_text(json.dumps(load(v+'-'+v+'-after-untied')['versions'],indent=2)+'\n')
print(json.dumps(summary,indent=2))
