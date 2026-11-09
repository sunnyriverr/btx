"""Exact release configure and dry-run only; no product compilation or unit execution."""
from pathlib import Path
import json,os,sys,subprocess,shutil,re,hashlib,datetime
import checkpoint
import integration_support as s
P=Path(__file__).resolve().parent;E=s.E;B=s.BUILD;ROOT=s.ROOT;SOURCE=s.SOURCE
TARGET='dac9aee53520bd49ed320ec7a49b9072fc7d88d9'
s.STATE=E/'maintained.json';s.R=json.loads(s.STATE.read_text());R=s.R
assert sys.argv[1]=='plan'
result={'target':TARGET,'saved_source':R['source'],'product_compilation_invoked':False,'unit_execution_invoked':False,'cache_save_requested':False,'status':'STARTED','commands':[]}
def save():
 result['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();(E/'release-plan.json').write_text(json.dumps(result,indent=2)+'\n')
def run(label,args,limit,cwd=SOURCE):
 s.need(label,args,limit,cwd=cwd);result['commands'].append(R['commands'][-1]);save()
try:
 assert R['status']=='RESTORED_VERIFIED'
 cp=json.loads((B/'btx-checkpoint.json').read_text());assert len(R['original_objects'])==5885
 baseline_binary=checkpoint.digest(B/'bin/test_btx.exe');assert baseline_binary=='31e45f1d0f2aed4168982120596182b5268057e1b9806960f27a60c769906bdd'
 oldcmd=json.loads((B/'compile_commands.json').read_text());shutil.copyfile(B/'compile_commands.json',E/'saved-compile-commands.json')
 run('release-fetch',['git','fetch','--no-tags','--depth=1','https://github.com/btxchain/btx.git',TARGET],180)
 run('release-checkout',['git','checkout','--detach',TARGET],90)
 catalog=s.catalog(TARGET,'release-before-configure');result['source_catalog_sha256']=checkpoint.digest(E/'release-before-configure-candidate-source.json')
 # Force any missing vcpkg package to fail rather than silently launch cold dependency builds.
 os.environ.update(VCPKG_ROOT=str(ROOT/'vcpkg'),VCPKG_DISABLE_METRICS='1',VCPKG_MAX_CONCURRENCY='2',VCPKG_BINARY_SOURCES='clear;files,'+str(ROOT/'binary-cache')+',read')
 args=list(R['actual_profile']['args']);assert args[0]=='cmake'and '-DWITH_MODELNET=ON'in args and '-DBUILD_TESTS=ON'in args
 args.append('-DVCPKG_INSTALL_OPTIONS=--only-binarycaching');result['configure_command']=args;save()
 run('release-configure',args,900)
 cache={}
 for l in(B/'CMakeCache.txt').read_text().splitlines():
  if l and not l.startswith(('#','//'))and '='in l:
   k,v=l.split('=',1);cache[k]=v
 for k in ['WITH_MODELNET:BOOL','BUILD_TESTS:BOOL','ENABLE_WALLET:BOOL','WITH_ZMQ:BOOL']:assert cache[k]=='ON',(k,cache.get(k))
 result['settings_delta']={k:[R['settings_before'].get(k),v]for k,v in cache.items()if R['settings_before'].get(k)!=v}
 newcmd=json.loads((B/'compile_commands.json').read_text());old={x['output']:x for x in oldcmd};new={x['output']:x for x in newcmd}
 changed=[k for k in old.keys()&new.keys()if old[k]!=new[k]]
 result['compile_commands']={'before':len(old),'after':len(new),'added':[new[k]for k in new.keys()-old.keys()],'removed':[old[k]for k in old.keys()-new.keys()],'changed_count':len(changed)}
 (E/'changed-compile-commands.json').write_text(json.dumps([{'before':old[k],'after':new[k]}for k in sorted(changed)],indent=2)+'\n');shutil.copyfile(B/'compile_commands.json',E/'release-compile-commands.json');shutil.copyfile(B/'CMakeCache.txt',E/'release-CMakeCache.txt')
 glob=B/'CMakeFiles/VerifyGlobs.cmake'
 if glob.exists():run('release-verify-globs',['cmake','-P',str(glob)],120,cwd=B)
 manifest=E/'release-manifest.ninja';shutil.copyfile(B/'build.ninja',manifest)
 targets=['btxd','btx-cli','btx-tx','btx-util','btx-open','btx-modeld','btx-guardd','btx-security','test_btx'];result['targets']=targets
 run('release-ninja-plan',['ninja','-C',str(B),'-f',str(manifest),'-n','-d','explain']+targets,180,cwd=B)
 text=(E/'release-ninja-plan.log').read_text(errors='replace');steps=re.findall(r'^\[(\d+)/(\d+)\]',text,re.M)
 result['planned_steps']=int(steps[-1][1])if steps else 0
 result['command_invalidations']=text.count('ninja explain: command line changed for ')
 result['stale_dependency_messages']=text.count('stored deps info out of date')
 result['plan_includes_regeneration']=bool(re.search('Re-running CMake|Re-checking globbed',text))
 result['planned_actions']=[l for l in text.splitlines()if re.match(r'^\[\d+/\d+\]',l)]
 run('release-ninja-targets',['ninja','-C',str(B),'-f',str(manifest),'-t','targets','all'],90,cwd=B)
 # All old objects and linked programs must remain byte-identical through this planning job.
 for k,v in R['original_objects'].items():assert checkpoint.digest(ROOT/k)==v['sha256'],k
 bins={k:v for k,v in cp['files'].items()if k.replace('\\','/').startswith('project-build/bin/')and k.endswith('.exe')}
 for k,v in bins.items():assert checkpoint.digest(ROOT/k)==v['sha256'],k
 assert checkpoint.digest(B/'bin/test_btx.exe')==baseline_binary
 assert s.catalog(TARGET,'release-after-plan')==catalog
 result.update(status='CONFIGURED_PLAN_READY',saved_objects_unchanged=5885,saved_binaries_unchanged=len(bins),baseline_binary_sha256=baseline_binary,source_unchanged=True)
except BaseException as e:
 result.update(status='CONFIGURE_OR_PLAN_BLOCKED',error=repr(e));raise
finally:
 s.quiesce();result['process_cleanup_verified']=not s.owned_processes();result['preserved_cache_id']=10173603864;result['cache_save_requested']=False;save()
