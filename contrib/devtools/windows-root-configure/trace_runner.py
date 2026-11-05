"""One owned native crash capture; original cached executable, no BTX compilation."""
from pathlib import Path
import os,sys,json,hashlib,subprocess,shutil,base64,re,struct,bisect,stat
import checkpoint
import integration_support as s
P=Path(__file__).resolve().parent;ROOT=s.ROOT;SOURCE=s.SOURCE;BUILD=s.BUILD;E=s.E
I=json.loads((P/'trace-inputs.json').read_text());s.STATE=E/'stack.json'
s.R=json.loads(s.STATE.read_text())if s.STATE.exists()else{'status':'SETUP','commands':[],'process_active':False,'scope':I['scope']}
R=s.R;sha=checkpoint.digest

def diff(a,b,prefix=''):
 out={}
 for k in sorted(set(a)|set(b)):
  x,y=a.get(k),b.get(k)
  if isinstance(x,dict)and isinstance(y,dict):out.update(diff(x,y,prefix+k+'.'))
  elif x!=y:out[prefix+k]=[x,y]
 return out

def pe(p):
 b=p.read_bytes();off=struct.unpack_from('<I',b,0x3c)[0];assert b[off:off+4]==b'PE\0\0'
 count=struct.unpack_from('<H',b,off+6)[0];size=struct.unpack_from('<H',b,off+20)[0];opt=off+24;assert struct.unpack_from('<H',b,opt)[0]==0x20b
 r={'image_base':struct.unpack_from('<Q',b,opt+24)[0]}
 for n in range(count):
  pos=opt+size+40*n
  if b[pos:pos+8].rstrip(b'\0')==b'.text':
   vs,rva,length,raw=struct.unpack_from('<IIII',b,pos+8);r.update(rva=rva,virtual_bytes=vs,raw_bytes=length,sha256=hashlib.sha256(b[raw:raw+length]).hexdigest())
 assert 'sha256'in r;return r

def validate_files(cp):
 changed=[]
 for name,x in cp['files'].items():
  f=checkpoint.checked(ROOT,name)
  if not f.is_file()or sha(f)!=x['sha256']:changed.append(name)
 assert not changed,changed
 return len(cp['files'])

def prepare():
 setup=json.loads((E/'result.json').read_text());assert setup['stages']['profile']=='COMPLETE'
 marker=BUILD/'btx-checkpoint.json';assert sha(marker)==I['checkpoint_sha256'];cp=json.loads(marker.read_text());assert cp['profile']['source']==I['source']
 d=diff(cp['profile']['actual_current_profile'],setup['profile']);allowed=json.loads((P/'profile-transition.json').read_text())['allowed_differences'];assert d in[{},allowed,{k:list(reversed(v))for k,v in allowed.items()}],d
 assert subprocess.check_output(['ninja','--version'],text=True).strip()=='1.13.2'
 bundle=E/'trace-source.bundle';bundle.write_bytes(base64.b64decode((P/'fixture-source.bundle.base64').read_text()));assert sha(bundle)==I['bundle_sha256']
 s.need('trace-public-parent',['git','fetch','--no-tags','--depth=2','https://github.com/sunnyriverr/btx.git',I['public_parent']],120)
 s.need('trace-bundle-verify',['git','bundle','verify',str(bundle)],60);s.need('trace-bundle-fetch',['git','fetch',str(bundle),I['bundle_ref']],60)
 s.need('trace-source-checkout',['git','checkout','--detach',I['source']],60)
 cat=s.catalog(I['source'],'trace-before');assert cat==cp['source_catalog'];R['restore']=checkpoint.restore(ROOT,SOURCE,cp['profile'],cat);assert R['restore']['restored']
 R['source']=I['source'];R['source_catalog_sha256']=sha(E/'trace-before-candidate-source.json');R['host_transition']=d;R['profile']=setup['profile']
 for flag in['WITH_MODELNET:BOOL=ON','BUILD_TESTS:BOOL=ON','ENABLE_WALLET:BOOL=ON','WITH_ZMQ:BOOL=ON']:assert flag in(BUILD/'CMakeCache.txt').read_text()
 exe=BUILD/'bin/windows_fixture_boundaries.exe';assert sha(exe)==I['binary_sha256']
 R['binary']={'path':str(exe),'sha256':sha(exe),'bytes':exe.stat().st_size,'pe':pe(exe)};R['before_files_verified']=validate_files(cp)
 R['modelnet_library_sha256']=sha(BUILD/'lib/bitcoin_modelnet.lib');assert R['modelnet_library_sha256']==I['modelnet_library_sha256']
 R['original_config']={n:sha(BUILD/n)for n in['build.ninja','CMakeFiles/rules.ninja','CMakeCache.txt','compile_commands.json']};assert s.resources()['disk_free']>3*1024**3
 # Standalone link-only graph. No object or library producer edges.
 block=I['component_link_block'].replace('bin\\windows_fixture_boundaries.exe','bin\\jit-symbols\\windows_fixture_boundaries.exe').replace('bin/windows_fixture_boundaries.exe','bin/jit-symbols/windows_fixture_boundaries.exe')
 block=block.replace('lib\\windows_fixture_boundaries.lib','lib\\jit_symbols.lib').replace('bin\\windows_fixture_boundaries.pdb','bin\\jit_symbols.pdb').replace('CMakeFiles\\windows_fixture_boundaries.rsp','CMakeFiles\\jit_symbols.rsp')
 lines=block.splitlines();assert sum(x.startswith('  LINK_FLAGS = ')for x in lines)==1
 lines=[x+' /MAP:'+str(E/'jit.map').replace('\\','/')if x.startswith('  LINK_FLAGS = ')else x for x in lines]
 graph=E/'symbols.ninja';graph.write_text('builddir = '+str(E/'symbol-logs').replace('\\','/')+'\ninclude CMakeFiles/rules.ninja\n\n'+'\n'.join(lines)+'\n');(BUILD/'bin/jit-symbols').mkdir(exist_ok=True)
 R['symbol_graph_sha256']=sha(graph);R['status']='PREPARED';s.save()

def build():
 assert R['status']=='PREPARED';common=['ninja','-C',str(BUILD),'-f',str(E/'symbols.ninja')]
 s.need('symbols-plan',common+['-n','-v','bin/jit-symbols/windows_fixture_boundaries.exe'],90)
 plan=(E/'symbols-plan.log').read_text(errors='replace');assert re.findall(r'^\[(\d+)/(\d+)\]',plan,re.M)==[('1','1')];assert 'Re-running CMake'not in plan and ' -c 'not in plan
 s.need('symbols-link',common+['-v','-j','1','bin/jit-symbols/windows_fixture_boundaries.exe'],180)
 aux=BUILD/'bin/jit-symbols/windows_fixture_boundaries.exe';R['auxiliary_pe']=pe(aux);R['text_mapping_identical']=R['auxiliary_pe']==R['binary']['pe'];assert R['text_mapping_identical'],[R['auxiliary_pe'],R['binary']['pe']]
 R['auxiliary_binary_sha256']=sha(aux);R['map_sha256']=sha(E/'jit.map')
 tool=E/'native_trace.exe';s.need('compile-trace',['clang-cl','/nologo','/std:c++20','/EHsc','/MT',str(P/'trace.cpp'),'/Fe'+str(tool),'/Fo'+str(E/'trace.obj'),'/link','dbghelp.lib'],120)
 R['trace_helper_sha256']=sha(tool);R['trace_source_sha256']=sha(P/'trace.cpp');R['status']='TRACE_READY';s.save()

def decode():
 text=(E/'trace.tsv').read_text();mmap=(E/'jit.map').read_text(errors='replace');pref=re.search(r'Preferred load address is\s+([0-9a-fA-F]+)',mmap);assert pref
 base=int(pref[1],16);assert base==R['binary']['pe']['image_base'];symbols=[]
 for line in mmap.splitlines():
  m=re.match(r'\s+[0-9a-fA-F]{4}:[0-9a-fA-F]+\s+(\S+)\s+([0-9a-fA-F]{16})\s+(.*)',line)
  if m:symbols.append((int(m[2],16)-base,m[1],m[3]))
 symbols.sort();positions=[x[0]for x in symbols];assert len(symbols)>1000
 main=[x.split('\t')for x in text.splitlines()if x.startswith('MAIN\t')];assert len(main)==1;loaded=int(main[0][1],16);events=[];current=None
 for line in text.splitlines():
  row=line.split('\t')
  if row[0]=='EXCEPTION':
   current={'number':int(row[1]),'thread':int(row[2]),'first_chance':bool(int(row[3])),'code':'0x'+row[4],'address':row[5],'parameters':row[6:],'frames':[]};events.append(current)
  elif row[0]=='FRAME'and current:
   pc=int(row[2],16);entry={'index':int(row[1]),'address':'0x'+row[2],'dbghelp':row[4],'module_base':'0x'+row[3]}
   if loaded+R['binary']['pe']['rva']<=pc<loaded+R['binary']['pe']['rva']+R['binary']['pe']['virtual_bytes']:
    rva=pc-loaded;i=bisect.bisect_right(positions,rva)-1
    if i>=0:
     a,name,obj=symbols[i];entry.update(rva=hex(rva),symbol=name,offset=hex(rva-a),object=obj)
   current['frames'].append(entry)
 R['map_symbols']=len(symbols);R['exceptions']=events;R['debugger_complete']='COMPLETE\t1\t'in text
 R['child_exit']=next((x.split('\t')[1]for x in text.splitlines()if x.startswith('EXIT\t')),None)
 assert R['debugger_complete']and R['child_exit']is not None
 R['loader_break_count']=sum(x.startswith('LOADER_BREAK\t')for x in text.splitlines())
 child_log=(E/'child.log').read_text(errors='replace')
 R['selected_case_entered']=bool(re.search(r'Entering test case "jit_api_priv_scale_journey_safety"',child_log))
 R['captured_failure_stack']=R['loader_break_count']==1 and R['selected_case_entered'] and any(
  any('symbol'in f for f in e['frames']) for e in events
  if e['code'] in ['0xc000001d','0xc0000409','0x80000003','0xc0000005'])
 R['daemon_frame_observed']=any('RunCapabilityDaemon'in f.get('symbol','')for e in events for f in e['frames'])
 tool=shutil.which('llvm-objdump')
 R['optional_callsite_disassembler']=tool
 if tool:
  chosen=[f for e in events for f in e['frames'] if 'RunCapabilityDaemon'in f.get('symbol','') or f.get('symbol')in['close','_close','_invalid_parameter_internal','_invalid_parameter_noinfo','_invoke_watson']]
  seen=set()
  for frame in chosen:
   address=base+int(frame['rva'],16)
   if address in seen:continue
   seen.add(address)
   s.run('trace-callsite-'+str(len(seen)),[tool,'--disassemble','--start-address='+hex(max(base+R['binary']['pe']['rva'],address-48)),'--stop-address='+hex(address+48),R['binary']['path']],40)
 (E/'decoded-stack.json').write_text(json.dumps({'source':I['source'],'original_binary':R['binary'],'text_mapping_identical':True,'symbols':len(symbols),'exceptions':events,'child_exit':R['child_exit']},indent=2)+'\n')

def run():
 assert R['status']=='TRACE_READY';exe=Path(R['binary']['path']);assert sha(exe)==I['binary_sha256']
 data=Path('D:/js'+os.environ['GITHUB_RUN_ID']);assert not data.exists();scratch=data/'temp';scratch.mkdir(parents=True);R['unit_data']=str(data);s.save()
 old={k:os.environ.get(k)for k in['TMP','TEMP']};cmd=[str(exe),'--run_test=modelnet_jit_tests/jit_api_priv_scale_journey_safety','--report_level=detailed','--log_level=test_suite','--','-testdatadir='+str(data/'node')]
 (E/'child-command.utf16').write_bytes(subprocess.list2cmdline(cmd).encode('utf-16le'));R['child_command']=cmd
 try:
  os.environ['TMP']=os.environ['TEMP']=str(scratch);s.need('native-trace',[str(E/'native_trace.exe'),str(exe),str(E/'child-command.utf16'),str(E)],110)
 finally:
  for k,v in old.items():
   if v is None:os.environ.pop(k,None)
   else:os.environ[k]=v
  R['owned_processes_before_cleanup']=s.owned_processes();s.quiesce();R['owned_data_before_cleanup']=[]
  for f in data.rglob('*'):
   st=f.lstat();R['owned_data_before_cleanup'].append({'path':str(f.relative_to(data)),'mode':st.st_mode,'attributes':getattr(st,'st_file_attributes',None),'bytes':st.st_size})
  R['harness_readonly_adjustments']=[];s.save()
  def permission_cleanup(func,path,exc):
   f=Path(path);assert data in f.parents and not f.is_symlink();assert not f.lstat().st_file_attributes&stat.FILE_ATTRIBUTE_REPARSE_POINT
   os.chmod(f,stat.S_IWRITE|stat.S_IREAD);R['harness_readonly_adjustments'].append(str(f.relative_to(data)));func(path)
  shutil.rmtree(data,onerror=permission_cleanup);R['owned_data_removed']=not data.exists();s.save()
 decode();R['status']='NATIVE_STACK_CAPTURED'if R['captured_failure_stack']else'NO_FAILURE_STACK';s.save();print('DECODED_STACK_JSON', (E/'decoded-stack.json').read_text(),flush=True)
 assert R['captured_failure_stack'] and R['daemon_frame_observed'],'Inconclusive daemon caller stack; no cause proof'

def verify():
 cp=json.loads((BUILD/'btx-checkpoint.json').read_text());R['after_files_verified']=validate_files(cp);assert sha(BUILD/'btx-checkpoint.json')==I['checkpoint_sha256']
 s.catalog(I['source'],'trace-after');assert sha(E/'trace-after-candidate-source.json')==R['source_catalog_sha256']
 assert all(sha(BUILD/n)==h for n,h in R['original_config'].items());assert sha(Path(R['binary']['path']))==I['binary_sha256']
 R['source_and_cached_files_unchanged']=True;R['cache_saved']=False;s.quiesce();s.save()

stage=sys.argv[1];failed=False
try:{'prepare':prepare,'build':build,'run':run,'verify':verify}[stage]()
except BaseException as e:failed=True;R.setdefault('failures',[]).append({'stage':stage,'error':str(e),'type':type(e).__name__});print(type(e).__name__,str(e),flush=True)
finally:s.save();print(json.dumps({k:R.get(k)for k in['status','text_mapping_identical','child_exit','captured_failure_stack','source_and_cached_files_unchanged','failures']},indent=2),flush=True)
raise SystemExit(1 if failed else 0)
