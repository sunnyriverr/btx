from pathlib import Path
import importlib.machinery,importlib.util,subprocess,json,contextlib,io
R=Path(__file__).parent
baseline=R/'baseline-wrapper';baseline.write_bytes(subprocess.check_output(['git','-C','work/btx-contributions','show','666673a3:contrib/modelnet/btx-model']))
def load(name,path):
 l=importlib.machinery.SourceFileLoader(name,str(path));s=importlib.util.spec_from_loader(name,l);m=importlib.util.module_from_spec(s);l.exec_module(m);return m
results={}
for variant,path in [('baseline',baseline),('candidate',R/'source/contrib/modelnet/btx-model')]:
 m=load(variant,path);calls=[];m._rpc_dev=lambda sock,method,variants:(calls.append((method,variants)) or {});m._emit_dev=lambda *a,**k:None
 m.cmd_mirror('unused',['--query','valid','--keep-latest','2']);m.cmd_mirror('unused',['--query','valid','--keep-latest','2'])
 keys=[p[0][0].get('idempotency_key') for method,p in calls];ok=all(isinstance(x,str) and x for x in keys) and keys[0]!=keys[1]
 results[variant]={'fresh_nonempty_key_per_invocation':ok,'key_lengths':[len(k) if k else 0 for k in keys]}
 if variant=='candidate':
  calls.clear();m.cmd_mirror('unused',[]);assert calls==[('getmodelmirror',[[]])]
  calls.clear();m.cmd_mirror('unused',['--query','valid','--idempotency-key','opaque-retry-key']);assert calls[0][1][0][0]['idempotency_key']=='opaque-retry-key'
  for args in [['--query','valid','--idempotency-key',''],['--query','valid','--idempotency-key',' '],['--idempotency-key','read-only']]:
   calls.clear()
   with contextlib.redirect_stderr(io.StringIO()):
    try:m.cmd_mirror('unused',args)
    except SystemExit as e:assert e.code==2
    else:raise AssertionError('Invalid option accepted')
   assert not calls
  results[variant]['readonly_explicit_and_invalid_controls']=True
assert not results['baseline']['fresh_nonempty_key_per_invocation'] and results['candidate']['fresh_nonempty_key_per_invocation']
(R/'local-verification.json').write_text(json.dumps(results,indent=2));print(results)
