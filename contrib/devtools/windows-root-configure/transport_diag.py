"""Two-case native Windows original-call diagnostic, never a product repair."""
from pathlib import Path
import base64,hashlib,json,os,re,shutil,stat,struct,subprocess,sys
import checkpoint
import integration_support as s
from batch_results import classify
from job_tree import ProcessTree
P=Path(__file__).resolve().parent;I=json.loads((P/'cloud-inputs.json').read_text());s.STATE=s.E/'maintained.json';s.R=json.loads(s.STATE.read_text());R=s.R;sha=checkpoint.digest
assert I['cases']==['modelnet_cloud_tests/cloud_https_not_stub_error','modelnet_cloud_tests/cloud_https_use_fake_false_error_is_not_stubbed']

def contained():
 tree=ProcessTree();globals()['process_tree']=tree;return tree

def mapped():
 R['unit_data']='D:/sd'+os.environ['GITHUB_RUN_ID'];root=Path(R['unit_data']);assert not Path('S:/').exists();root.mkdir(exist_ok=True);(root/'tmp').mkdir(exist_ok=True);s.need('map-'+sys.argv[1],['subst','S:',str(root)],15);os.environ['TMP']=os.environ['TEMP']='S:/tmp';s.save()

def unmap():
 s.need('unmap-'+sys.argv[1],['subst','S:','/D'],15);R['short_drive_removed']=not Path('S:/').exists();s.save();assert R['short_drive_removed']

def one(label,selector,traced):
 report=s.E/(label+'.xml');trace=s.E/(label+'.bin');assert not trace.exists()
 prior=os.environ.pop('BTX_S3_CALL_TRACE_FILE',None)
 if traced:os.environ['BTX_S3_CALL_TRACE_FILE']=str(trace)
 try:
  cmd=[str(s.BUILD/'bin/test_btx.exe'),'--run_test='+selector,'--log_level=message','--report_level=detailed','--report_format=XML','--report_sink='+str(report),'--catch_system_errors=yes','--','-testdatadir=S:/f'];rc=s.run(label,cmd,60)
 finally:
  os.environ.pop('BTX_S3_CALL_TRACE_FILE',None)
  if prior is not None:os.environ['BTX_S3_CALL_TRACE_FILE']=prior
 log=(s.E/(label+'.log')).read_text(errors='replace');v=classify([selector],log,report.read_text() if report.exists() else '',rc);assert v['state']=='failed' and v['cases'][selector]['result']=='aborted';assert 'Invalid parameter detected by C runtime library' in log;assert 'BTX_S3_TRACE_IO_ERROR' not in log;assert globals()['process_tree'].active()==1
 item={'label':label,'result':v,'trace_requested':traced}
 if traced:
  raw=trace.read_bytes();assert raw and len(raw)%80==0;rows=[]
  for off in range(0,len(raw),80):
   row=list(struct.unpack('<10Q',raw[off:off+80]));assert row[0]==I['schema']['magic'];rows.append(row)
  last=rows[-1];assert last[1]==6 and str(last[2]) in I['schema']['sites'];assert I['schema']['sites'][str(last[2])]['call']=='::close(fd)';assert last[7]==0 and last[8]==1,'Before-close value not a valid stream socket';assert last[3]<(1<<31)
  item.update(trace_sha256=sha(trace),trace_records=rows,original_call='::close(fd)',original_line=last[2],socket_fd=last[3],valid_winsock_stream=True,crt_alias_address_equal=last[9]==1,unmatched_before_phase=6)
 else:assert not trace.exists()
 R.setdefault('transport_cases',{})[label]=item;s.save();return item

def baseline():
 tree=contained();assert R['status']=='RESTORED_VERIFIED' and not s.owned_processes();assert sha(s.BUILD/'bin/test_btx.exe')==I['binary_sha256'];s.need('cloud-before-inventory',[str(s.BUILD/'bin/test_btx.exe'),'--list_content'],30);R['baseline_inventory_sha256']=sha(s.E/'cloud-before-inventory.log')
 entries=json.loads((s.BUILD/'compile_commands.json').read_text());matches=[x for x in entries if x['file'].replace('\\','/').endswith('/src/modelnet/s3_client.cpp')];assert len(matches)==1;R['s3_compile_command']=matches[0];obj=Path(matches[0]['output']);obj=obj if obj.is_absolute() else s.BUILD/obj;R['s3_object_path']=str(obj);s.need('original-s3-symbols',['dumpbin','/symbols',str(obj)],60);s.need('original-unit-imports',['dumpbin','/imports',str(s.BUILD/'bin/test_btx.exe')],60)
 excerpts=[]
 for folder in os.environ['INCLUDE'].split(';'):
  h=Path(folder)/'io.h'
  if h.exists():
   lines=h.read_text(errors='replace').splitlines()
   for n,line in enumerate(lines):
    if re.search(r'\b_?close\s*\(',line):excerpts.extend([str(h)+':'+str(n+1)]+lines[max(0,n-3):n+3])
 (s.E/'native-close-declarations.txt').write_text('\n'.join(excerpts)+'\n');assert excerpts
 mapped()
 try:
  for n,selector in enumerate(I['cases']):one('before-'+str(n),selector,False)
  assert sha(s.BUILD/'bin/test_btx.exe')==I['binary_sha256'];R['baseline_verified']=True;R['status']='TRANSPORT_BASELINE_CONFIRMED';s.save()
 finally:unmap()

def build():
 tree=contained();assert R['baseline_verified'] and not s.owned_processes();bundle=s.E/'diagnostic-candidate.bundle';bundle.write_bytes(base64.b64decode((P/'diagnostic.bundle.base64').read_text()));assert sha(bundle)==I['bundle_sha256'];s.need('cloud-bundle-verify',['git','bundle','verify',str(bundle)],30);s.need('cloud-bundle-fetch',['git','fetch',str(bundle),I['bundle_ref']],30)
 changed=subprocess.check_output(['git','diff','--name-only',I['integration_base'],I['integration']],cwd=s.SOURCE,text=True).splitlines();assert changed==I['changed_files'];s.need('cloud-candidate-checkout',['git','checkout','--detach',I['integration']],30);assert subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=s.SOURCE,text=True).strip()==I['tree']
 for name in changed:assert sha(s.SOURCE/name)==I['candidate_file_sha256'][name]
 candidate=s.catalog(I['integration'],'cloud-before');assert set(candidate['files'])==set(R['source_catalog']['files']);assert [k for k in candidate['files'] if candidate['files'][k]!=R['source_catalog']['files'][k]]==changed;R['candidate_catalog']=candidate;assert not subprocess.check_output(['git','diff','--name-only'],cwd=s.SOURCE,text=True).strip()
 manifest=s.E/'cloud-verified.ninja';shutil.copyfile(s.BUILD/'build.ninja',manifest);assert sha(manifest)==R['original_config']['build.ninja'];R['frozen_manifest_sha256']=sha(manifest);common=['ninja','-C',str(s.BUILD),'-f',str(manifest)]
 s.need('cloud-unit-plan',common+['-n','-d','explain','test_btx'],60);plan=(s.E/'cloud-unit-plan.log').read_text(errors='replace');steps=re.findall(r'^\[(\d+)/(\d+)\]',plan,re.M);R['cloud_planned_steps']=int(steps[-1][1]) if steps else 0;assert 0<R['cloud_planned_steps']<=60;assert 'command line changed for ' not in plan and 'Re-running CMake' not in plan
 objects=re.findall(r'Building CXX object ([^\r\n]+\.obj)',plan);R['cloud_planned_objects']=objects;R['planned_executable_links']=re.findall(r'Linking CXX executable bin[\\/]([^\r\n]+)\.exe',plan);assert set(R['planned_executable_links'])<=set(['test_btx','btxd','btx-open','btx-modeld']);allowed=['s3_client.cpp.obj','clientversion.cpp.obj','matmul_v4_rc_production_canary.cpp.obj','matmul_v4_rc_production_golden_manifest.cpp.obj'];assert all(any(x.endswith(z) for z in allowed) for x in objects),objects;assert all(any(x.endswith(z) for x in objects) for z in allowed[:1]);R['status']='CLOUD_R2_BUILDING';s.save()
 s.need('cloud-unit-build',common+['-j','4','-k','1','test_btx'],900)
 for name,value in R['original_config'].items():assert sha(s.BUILD/name)==value,name
 R['candidate_binary_sha256']=sha(s.BUILD/'bin/test_btx.exe');assert R['candidate_binary_sha256']!=I['binary_sha256'];header=(s.BUILD/'src/bitcoin-build-info.h').read_text();assert I['integration'][:7] in header and re.search(r'BUILD_GIT_DIRTY\s+0',header);R['build_info']=header
 s.need('cloud-after-inventory',[str(s.BUILD/'bin/test_btx.exe'),'--list_content'],30);before=(s.E/'cloud-before-inventory.log').read_bytes();after=(s.E/'cloud-after-inventory.log').read_bytes();names=[x.split('/',1)[1].encode() for x in I['new_controls']];lines=after.splitlines(keepends=True);removed=[x for x in lines if any(x.strip().startswith(n+b'*') for n in names)];assert len(removed)==len(I['new_controls']),removed;assert b''.join(x for x in lines if x not in removed)==before;R['inventory_delta_controls']=I['new_controls'];R['status']='CLOUD_R2_LINKED';s.save();assert tree.active()==1

def diagnose():
 tree=contained();assert R['status']=='CLOUD_R2_LINKED' and not s.owned_processes();s.need('diagnostic-s3-symbols',['dumpbin','/symbols',R['s3_object_path']],60);s.need('diagnostic-unit-imports',['dumpbin','/imports',str(s.BUILD/'bin/test_btx.exe')],60);mapped()
 try:
  for n,selector in enumerate(I['cases']):
   item=one('after-'+str(n),selector,True);prior=R['transport_cases']['before-'+str(n)]['result']['cases'][selector];current=item['result']['cases'][selector];assert prior==current,'Diagnostic altered observable case outcomes'
  assert sha(s.BUILD/'bin/test_btx.exe')==R['candidate_binary_sha256'];R['status']='S3_CRT_CALL_LOCALIZED';s.save()
 finally:unmap()

def retain():
 assert not R['process_active'];R['owned_processes_before_cleanup']=s.owned_processes();s.quiesce();assert not R['owned_processes_before_cleanup'] and R.get('short_drive_removed',True)
 if R.get('unit_data'):
  root=Path(R['unit_data']);assert root==Path('D:/sd'+os.environ['GITHUB_RUN_ID'])
  def readonly(fn,name,exc):
   f=Path(name);assert f.resolve().is_relative_to(root.resolve())
   if not isinstance(exc[1],PermissionError) or f.stat().st_mode&stat.S_IWRITE:raise exc[1]
   os.chmod(f,stat.S_IREAD|stat.S_IWRITE);fn(name)
  if root.exists():shutil.rmtree(root,onerror=readonly)
  R['runtime_data_removed']=not root.exists()
 assert R['status']=='S3_CRT_CALL_LOCALIZED' and R['runtime_data_removed'];assert s.catalog(I['integration'],'diagnostic-after')==R['candidate_catalog']
 for name,value in R['original_config'].items():assert sha(s.BUILD/name)==value,name
 changes=[]
 for name,item in R['original_objects'].items():
  assert (s.ROOT/name).is_file(),name
  if sha(s.ROOT/name)!=item['sha256']:changes.append(name)
 planned={'project-build/'+x.replace('\\','/') for x in R['cloud_planned_objects']};assert all(x.replace('\\','/') in planned for x in changes),changes;R['changed_objects']=changes;R['original_objects_retained']=len(R['original_objects'])
 for name,item in R['dependencies_before'].items():assert sha(s.ROOT/name)==item['sha256'],name
 R['binaries']={name:sha(s.BUILD/'bin'/(name+'.exe')) for name in ['btxd','btx-cli','btx-tx','btx-util','btx-open','btx-modeld','test_btx']};cp=json.loads((s.BUILD/'btx-checkpoint.json').read_text());R['unchanged_binaries']={name:R['binaries'][name]==next(x['sha256'] for file,x in cp['files'].items() if file.replace('\\','/').endswith('/bin/'+name+'.exe')) for name in R['binaries']};assert all(ok for name,ok in R['unchanged_binaries'].items() if name not in R['planned_executable_links']);assert R['binaries']['test_btx']==R['candidate_binary_sha256'];R['project_cache_saved']=False;R['retention_verified']=True;s.save()
try:{'baseline':baseline,'build':build,'diagnose':diagnose,'retain':retain}[sys.argv[1]]()
except BaseException as e:R.setdefault('diagnostic_failures',[]).append({'stage':sys.argv[1],'type':type(e).__name__,'error':str(e)});s.save();raise
finally:s.save()
