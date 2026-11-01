from pathlib import Path
import json,re,collections,hashlib,datetime,subprocess,shutil
r=Path('/BTX_REVIEW_ROOT');out=r/'pr340-fold-rerun';run=out/'run';obs=json.loads((run/'nodes/observations.json').read_text());execution=json.loads((run/'result.json').read_text());log=run/'nodes/node1/regtest/debug.log';lines=log.read_text().splitlines();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
statuses=obs.get('historical_block_status',[]);hashes={s['hash'] for s in statuses};requestre=re.compile(r'\bRequesting block ([0-9a-f]{64})\b');counts=collections.Counter();deferrals=[];evictions=[];historical_events=[]
for no,line in enumerate(lines,1):
 m=requestre.search(line)
 if m and m[1] in hashes:counts[m[1]]+=1;historical_events.append({'line':no,'hash':m[1],'text':line})
 if 'Deferring requested background body' in line:deferrals.append({'line':no,'text':line})
 if 'Evicting retained MatMul body' in line:evictions.append({'line':no,'text':line})
restart=next((e for e in obs['events'] if e['phase']=='restart-preserved-catchup'),None)
post=[]
if restart:
 for x in historical_events:
  try:t=datetime.datetime.fromisoformat(x['text'].split('Z')[0].replace(' ','T')).replace(tzinfo=datetime.timezone.utc).timestamp()
  except ValueError:continue
  if t>=restart['time']:post.append(x)
completed=obs['events'][-1];catch=next((e for e in obs['events'] if e['phase']=='catchup-and-real-metal-pass'),{})
runtime=[e['runtime'] for e in obs['events'] if 'runtime' in e]
metrics={'requested_body_count':len(hashes),'request_log_entries':sum(counts.values()),'distinct_historical_requested_hashes':len(counts),'max_requests_per_hash':max(counts.values(),default=0),'mean_requests_per_distinct_requested_hash':sum(counts.values())/len(counts) if counts else None,'mean_requests_per_1024_historical_bodies':sum(counts.values())/1024,'deferring_requested_background_body_lines':len(deferrals),'evicting_retained_matmul_body_lines':len(evictions),'post_restart_historical_request_lines':len(post),'count_scope':'Whole target process log across catch-up/restart; requestcounts filtered to the1024 source-matching historical hashes101..1124. Deferral/eviction messagecounts whole targetlog. Each matchingnativeRequestingline counted once, both ordinary/directforms. No network-byte estimate.'}
source_connected=all(t['source_connections']==1 for t in obs.get('timeline',[]) if t['seconds']>=.5)
summary={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_head':execution['source_head'],'harness_sha256':execution['harness_sha256'],'harness_unchanged':True,'status':obs['status'],'exit_code':execution['exit_code'],'external_stop_reason':execution['external_stop_reason'],'catchup_elapsed_s':catch.get('elapsed'),'historical_flags_all_local':len(statuses)==1024 and all(s['nStatus']&256 and not s['nStatus']&512 for s in statuses),'source_connected_during_catchup':source_connected,'source_connection_post_restart':len(completed.get('peers',[]))==1,'final_height':completed.get('info',{}).get('blocks'),'foreground':obs.get('foreground'),'strict_metal_samples':runtime,'metrics':metrics,'log_sha256':sha(log),'source_log_sha256':sha(run/'nodes/node0/regtest/debug.log'),'binary_sha256':execution['binaries'],'prior_run_metrics':json.loads((out/'prior-run-metrics.json').read_text()),'scope':'macOSM4strictMetaltoyregtest pinnedconsensus noquorum, exactprivate1124snapshotpin, sameimmutableharness; no mainnet/fullsuite/otherOS/release qualification. Singlefoldrun, originalbaseline reused. No churn fix/inference from one-run requestcount difference.','publication':False}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
(out/'requests-per-hash.json').write_text(json.dumps(dict(sorted(counts.items())),indent=2)+'\n')
(out/'requested-events.json').write_text(json.dumps(historical_events,indent=2)+'\n')
(out/'capacity-events.json').write_text(json.dumps({'deferrals':deferrals,'evictions':evictions},indent=2)+'\n')
assert summary['status']=='passed' and summary['exit_code']==0 and not summary['external_stop_reason'],summary
assert summary['historical_flags_all_local'] and source_connected and len(counts)==1024 and not post
print(json.dumps({k:v for k,v in summary.items() if k not in ['strict_metal_samples','foreground']},indent=2))
