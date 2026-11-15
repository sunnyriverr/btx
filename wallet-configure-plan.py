import os,subprocess,json,time,hashlib,pathlib,shutil,re
r=pathlib.Path('records');r.mkdir(exist_ok=True);source=pathlib.Path('source').resolve();build=pathlib.Path('build').resolve();pin='61f13b8870ed98c7b10db2e32c04fb647023f4ef';began=time.monotonic();result={'source_pin':pin,'BTX_compile_invoked':False,'tests_invoked':False,'cache_restored':False,'cache_reason':'No independent profile/source-compatible cache qualified; configure-only does not need old objects.'}
def run(name,args,timeout=300):
 with (r/(name+'.log')).open('w') as f:p=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,text=True,timeout=timeout)
 result[name]={'exit':p.returncode,'command':args};return p.returncode
try:
 assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==pin
 result['disk_before']=shutil.disk_usage('.')._asdict();result['memory_before']=pathlib.Path('/proc/meminfo').read_text();assert shutil.disk_usage('.').free>15*2**30
 run('toolchain',['bash','-c','uname -a; cmake --version; ninja --version; c++ --version; python3 --version; dpkg-query -W libsqlite3-dev libevent-dev libssl-dev libboost-dev'])
 opts={'BUILD_DAEMON':'ON','BUILD_CLI':'ON','ENABLE_WALLET':'ON','WITH_SQLITE':'ON','WITH_BDB':'OFF','BUILD_GUI':'OFF','BUILD_TESTS':'OFF','BUILD_GUI_TESTS':'OFF','BUILD_BENCH':'OFF','BUILD_FUZZ_BINARY':'OFF','BUILD_TX':'OFF','BUILD_UTIL':'OFF','BUILD_WALLET_TOOL':'OFF','WITH_MODELNET':'OFF','WITH_ZMQ':'OFF','BTX_ENABLE_CUDA_EXPERIMENTAL':'OFF','ENABLE_EXTERNAL_SIGNER':'OFF','WITH_CCACHE':'OFF'}
 args=['cmake','-S',str(source),'-B',str(build),'-G','Ninja','-DCMAKE_BUILD_TYPE=Release']+['-D'+k+'='+v for k,v in opts.items()]
 assert run('configure',args,600)==0,'configure failed; no build attempted'
 cache=(build/'CMakeCache.txt').read_text();(r/'CMakeCache.txt').write_text(cache)
 for k,v in opts.items():assert re.search(r'^'+re.escape(k)+r':[^=]+='+v+r'$' ,cache,re.M),k
 assert run('ninja-dry-run',['ninja','-C',str(build),'-n','btxd','btx-cli'],180)==0
 assert run('ninja-commands',['ninja','-C',str(build),'-t','commands','btxd','btx-cli'],180)==0
 text=(r/'ninja-dry-run.log').read_text();result['planned_steps']=sum(1 for l in text.splitlines() if l.startswith('['));result['planned_object_steps']=text.count('Building CXX object')+text.count('Building C object');result['dry_run_tail']=text.splitlines()[-8:]
 config=build/'test/config.ini';assert config.is_file();(r/'config.ini').write_bytes(config.read_bytes())
 result['BTX_object_files_found']=[str(p.relative_to(build)) for p in build.rglob('*') if p.is_file() and p.suffix in ['.o','.obj'] and not any(x in str(p) for x in ['CMakeScratch','CompilerId','CMakeTmp'])];assert not result['BTX_object_files_found']
 result['BTX_binaries_found']=[str(p) for p in (build/'bin').glob('*') if p.is_file()];assert not result['BTX_binaries_found'];result['status']='CONFIGURE_AND_DRY_RUN_PASS'
except BaseException as e:result['status']='SETUP_OR_CONFIGURE_FAILED';result['error']=str(e);raise
finally:
 result['elapsed_s']=round(time.monotonic()-began,2);result['disk_after']=shutil.disk_usage('.')._asdict();result['configured_build_bytes']=sum(p.stat().st_size for p in build.rglob('*') if p.is_file());result['compiler_detection_probes']='CMake may compile/run toolchain capability probes; no BTX target build requested';(r/'result.json').write_text(json.dumps(result,indent=2)+'\n')
