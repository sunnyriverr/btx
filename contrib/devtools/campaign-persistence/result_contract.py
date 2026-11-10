"""Offline observation contract. Findings are not a product PASS or native execution."""
import copy,json
GATES=('exact_binary_identity','supported_nonspending_request','normal_save_restart',
 'campaign_save_failure_confirmed','same_failure_held_through_stop','restart_observed',
 'fault_removed','normal_write_recovery','clean_shutdown','owned_runtime_removed')
def classify(r):
 missing=[k for k in GATES if r.get(k) is not True]
 if missing or r.get('error') or r.get('cleanup_signals')!=[] or r.get('leftovers')!=[]:
  return {'outcome':'INCOMPLETE','missing':missing}
 for k in ('rpc_acknowledged','memory_changed','disk_changed','restart_retained_change'):
  if type(r.get(k)) is not bool:return {'outcome':'INCOMPLETE','missing':[k]}
 if r['rpc_acknowledged'] and r['memory_changed'] and not r['restart_retained_change']:
  return {'outcome':'ACKNOWLEDGED_CHANGE_LOST_ON_RESTART','disk_changed':r['disk_changed']}
 if not r['rpc_acknowledged']:
  return {'outcome':'CALLER_REPORTED_FAILURE','memory_changed':r['memory_changed']}
 if r['restart_retained_change']:
  return {'outcome':'ACKNOWLEDGED_CHANGE_SURVIVED','disk_changed':r['disk_changed']}
 return {'outcome':'UNRESOLVED','missing':[]}
def offline_checks():
 r=dict.fromkeys(GATES,True);r.update(rpc_acknowledged=True,memory_changed=True,disk_changed=False,restart_retained_change=False,cleanup_signals=[],leftovers=[])
 assert classify(r)['outcome']=='ACKNOWLEDGED_CHANGE_LOST_ON_RESTART'
 count=0
 for k in GATES:
  for bad in (False,None,'true'):
   x=copy.deepcopy(r);x[k]=bad;assert classify(x)['outcome']=='INCOMPLETE';count+=1
 for k in ('rpc_acknowledged','memory_changed','disk_changed','restart_retained_change'):
  x=copy.deepcopy(r);x[k]=None;assert classify(x)['outcome']=='INCOMPLETE';count+=1
 for k in ('leftovers','cleanup_signals'):
  x=copy.deepcopy(r);x[k]=[123];assert classify(x)['outcome']=='INCOMPLETE';count+=1
 x=copy.deepcopy(r);x['rpc_acknowledged']=False;assert classify(x)['outcome']=='CALLER_REPORTED_FAILURE'
 x=copy.deepcopy(r);x['disk_changed']=True;x['restart_retained_change']=True;assert classify(x)['outcome']=='ACKNOWLEDGED_CHANGE_SURVIVED'
 return {'offline_only':True,'negative_controls':count,'classification_controls':3,'pass':True}
if __name__=='__main__':print(json.dumps(offline_checks()))
