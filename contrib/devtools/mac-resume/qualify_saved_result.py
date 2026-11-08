"""Offline qualification of retained native observations; never changes raw CI result."""
from pathlib import Path
import json,hashlib,copy,shlex,re
P=Path(__file__).resolve().parent
PROBE='mac-config-build/src/libbitcoinpqc/shake_a64_probe/build/CMakeFiles/shake_a64_probe.dir/shake_a64_probe.s.o'
ROOT='/Users/runner/work/btx/btx/'
def sha(b):return hashlib.sha256(b).hexdigest()
def qualify(state,inv,db,plan,expected,graphs):
 assert state['checks']['exact_content_modes_ns_mtimes_links_restored'] and state['checks']['fresh_git_identity_preserved'] and state['checks']['fresh_command_graph_matches']
 assert all(sha(g)==expected['commands_sha256'] for g in graphs)
 allobjs={n for n in inv if n.startswith('mac-config-build/') and n.endswith('.o')}
 targets=set()
 for line in graphs[1].decode().splitlines():
  args=shlex.split(line)
  for k,token in enumerate(args[:-1]):
   if token=='-o' and args[k+1].endswith('.o'):
    n=args[k+1];targets.add(n.removeprefix(ROOT) if n.startswith('/') else 'mac-config-build/'+n)
 # The selected Ninja graph includes dependency objects omitted from the root
 # compile database (39 LevelDB entries); do not misclassify those as probes.
 retained=allobjs & targets
 assert len(allobjs)==expected['object_count'] and len(retained)==expected['target_object_count'] and allobjs-retained=={PROBE}
 assert PROBE not in targets
 audits=state['object_phase_audits']
 assert set(audits)=={'before_plans','after_initial_dry_plan','after_configure','after_command_inspection','after_final_dry_plan','final'}
 for phase,a in audits.items():
  assert a['changed_count']==len(a['changed']),'Truncated differences cannot qualify'
  assert len(a['changed'])==(0 if phase in ['before_plans','after_initial_dry_plan'] else 1)
  for delta in a['changed']:
   assert delta['path']==PROBE and delta['expected']=={'sha256':inv[PROBE]['sha256'],'mtime_ns':inv[PROBE]['mtime_ns']}
   assert delta['actual']['sha256']==delta['expected']['sha256'],'Probe byte changes are not exempt'
   assert delta['actual']['mtime_ns']!=delta['expected']['mtime_ns']
 for n in retained:
  rel=n.removeprefix('mac-config-build/')
  assert 'Building CXX object '+rel not in plan and 'Building C object '+rel not in plan and 'Building ASM object '+rel not in plan,('Retained target scheduled',n)
 assert 'Re-running CMake' not in plan
 actions=re.findall(r'^\[(\d+)/(\d+)\]',plan,re.M);assert actions and actions[-1][0]==actions[-1][1]
 return {'qualified':True,'restored_entries':len(inv),'retained_target_objects_unchanged_and_not_scheduled':len(retained),'configure_probe_identical_bytes_new_mtime':1,'remaining_inspected_actions':int(actions[-1][1]),'raw_native_job_conclusion':state.get('raw_ci_conclusion','not_assigned'),'inspection':'Explicit configuration, then include-wrapper manifest under Ninja -n only; not ordinary manifest regeneration execution or a subsequent compile'}
def main():
 d=P/'run-42485162075';state=json.loads((d/'restore-records/restore-result.json').read_text());inv=json.loads((P.parent/'compile-chunk/retry1/run-42476421106/chunk-records/checkpoint-input.json').read_text());db=json.loads((d/'mac-config-records/compile_commands.json').read_text());plan=(d/'restore-records/restored-final-dry-plan.log').read_text();expected=json.loads((P/'expected.json').read_text());graphs=[(d/'restore-records'/n).read_bytes() for n in ['restored-command-graph.log','inspection-command-graph.log']]
 assert state['error']=="AssertionError('Completed object content/mtime changed; inspect phase audits')", 'Unexpected failure remains unresolved'
 state['raw_ci_conclusion']='failure_preserved'
 result=qualify(state,inv,db,plan,expected,graphs)
 cases={}
 for name,mut in [('target_content_change',lambda s:s['object_phase_audits']['final']['changed'].append({'path':next(n for n in inv if n.endswith('.o') and n!=PROBE),'actual':{'sha256':'bad'}})),('probe_content_change',lambda s:s['object_phase_audits']['final']['changed'][0]['actual'].update(sha256='bad')),('unknown_change',lambda s:s['object_phase_audits']['final']['changed'][0].update(path='mac-config-build/unknown.o')),('truncated_differences',lambda s:s['object_phase_audits']['final'].update(changed_count=2))]:
  mutant=copy.deepcopy(state);mut(mutant)
  if name=='target_content_change':mutant['object_phase_audits']['final']['changed_count']=2
  try:qualify(mutant,inv,db,plan,expected,graphs)
  except (AssertionError,KeyError):cases[name]='rejected'
  else:raise AssertionError(name+' accepted')
 target=next(n for n in inv if n.endswith('.o') and n!=PROBE)
 try:qualify(state,inv,db,plan+'\nBuilding CXX object '+target.removeprefix('mac-config-build/'),expected,graphs)
 except AssertionError:cases['retained_target_rescheduled']='rejected'
 else:raise AssertionError('Rebuild accepted')
 try:qualify(state,inv,db,plan,expected,[b'changed graph',graphs[1]])
 except AssertionError:cases['changed_command_graph']='rejected'
 else:raise AssertionError('Graph change accepted')
 result['offline_negative_controls']=cases;result['native_run']=42485162075;result['fixture']='ce9e0f3f89aea7a4a1df682384548e330a2cc854';result['source']='ff5f3f04ea11f044594987fc6be043ff68b136ad'
 (P/'qualification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
