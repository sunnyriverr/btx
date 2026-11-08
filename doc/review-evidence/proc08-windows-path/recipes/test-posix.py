from pathlib import Path
import subprocess as sp,json,hashlib,shutil
P=Path('work/btx-lanes/session-1/windows_integrated_native_acceptance/unit-fixture-portability').resolve();F=P/'current-full-resume/four-fixture-repair/runtime-prerequisites/proc08-path-repair';D=F.parent/'pending-primitives-recovery/proc08-diagnostic';G=P/'product.git';C=json.loads((F/'candidate.json').read_text());S=F/'posix-source';S.mkdir(exist_ok=True)
headers=['src/modelnet/proc08/proc08.h','src/modelnet/nifdt_contract/contract.h','src/util/fs.h','src/tinyformat.h','src/attributes.h'];hashes={}
tree=set(sp.check_output(['git','--git-dir='+str(G),'ls-tree','-r','--name-only',C['base']],text=True).splitlines())
import re
while headers:
 name=headers.pop()
 if name in hashes:continue
 b=sp.check_output(['git','--git-dir='+str(G),'show',C['base']+':'+name]);p=S/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);hashes[name]=hashlib.sha256(b).hexdigest()
 for h in re.findall(r'^#include [<"]([^>"]+)[>"]',b.decode(),re.M):
  if 'src/'+h in tree:headers.append('src/'+h)
probe=(D/'probe.cpp').read_text();probe=probe.replace('    return 0;\n}',r'''    const fs::path literal=base/"proc08-evidence\\a.txt";
    const fs::path literal_inside=root/"part\\leaf.txt";
    { std::ofstream out{literal,std::ios::binary};out<<"literal";if(!out)return 4; }
    { std::ofstream out{literal_inside,std::ios::binary};out<<"inside";if(!out)return 5; }
    if(fs::equivalent(file,literal))return 6;
    Run("literal_backslash_outside",fs::PathToString(literal),r);
    Run("literal_backslash_inside",fs::PathToString(literal_inside),r);
    Run("trailing_root",r,r+"/");
    return 0;
}''')
(F/'posix-probe.cpp').write_text(probe);runtime=F/'posix-runtime';assert not runtime.exists();result=[]
try:
 for label,commit in [('before',C['before']),('after',C['target'])]:
  prod=sp.check_output(['git','--git-dir='+str(G),'show',commit+':src/modelnet/proc08/proc08.cpp']);(S/'src/modelnet/proc08/proc08.cpp').write_bytes(prod)
  exe=F/('posix-'+label);cmd=['clang++','-std=c++20','-Wall','-Wextra','-Werror','-I'+str(S/'src'),str(F/'posix-probe.cpp'),str(S/'src/modelnet/proc08/proc08.cpp'),'-o',str(exe)]
  compile=sp.run(cmd,capture_output=True,text=True);(F/('posix-'+label+'-compile.log')).write_text(compile.stdout+compile.stderr);assert compile.returncode==0,compile.stderr
  run=sp.run([str(exe),str(runtime)],capture_output=True,text=True);(F/('posix-'+label+'.jsonl')).write_text(run.stdout);assert run.returncode==0,run.stderr
  rows=[json.loads(x)for x in run.stdout.splitlines()];assert rows[0]['same_file_mixed'] and rows[0]['same_file_forward']
  for row in rows[1:]:
   labelcase=row['case'];expected=labelcase.startswith(('outside_','prefix_sibling_'))or labelcase=='literal_backslash_outside';err=''if expected else 'FIELD'if labelcase=='empty'else 'ABSENT'if labelcase=='missing_outside'else 'INSIDE';assert(row['accepted'],row['error'],row['research_outside'])==(expected,err,expected),row
   assert not any(row[x]for x in ['release_qualified','gpu_passed','windows_passed'])
  result.append(dict(stage=label,source=commit,commands=cmd,compiler=sp.check_output(['clang++','--version'],text=True).splitlines()[0],binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),observations=rows))
  shutil.rmtree(runtime)
 assert result[0]['observations']==result[1]['observations']
 (F/'posix-verification.json').write_text(json.dumps(dict(platform=sp.check_output(['uname','-sm'],text=True).strip(),component_native_execution=True,full_btx_suite=False,headers=hashes,results=result,identical_behavior=True,runtime_removed=not runtime.exists()),indent=2)+'\n');print('POSIX before/after:17 identical actual-component observations each; literal backslash and outside/refusal controls passed')
finally:
 if runtime.exists():shutil.rmtree(runtime)
