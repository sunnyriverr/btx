from pathlib import Path
import os,json,hashlib,subprocess,shlex,time
w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'records';p=w/'proposal';src=w/'product';build=w/'gui-pilot-runtime/qtbuild';r={'complete':False,'product_modified':False,'production_recompiled':False,'new_compile_actions':1}
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def run(cmd,label,cwd=None,limit=180):
 z=subprocess.run([str(x)for x in cmd],cwd=cwd or w,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=limit);(out/(label+'.log')).write_bytes(z.stdout);print(label,z.returncode,flush=True);assert z.returncode==0,label;return z.stdout.decode()
try:
 assert json.loads((out/'staging.json').read_text())['complete']
 expected='b256fded8c1d823a38eb2b2dfcfa72d1cd4b3507e006bce04dfdecd54ee350f1';assert sha(src/'src/modelnet/s3_store.cpp')==expected
 r['s3_store_sha256']=expected;r['retained_composition']=json.loads((out/'staging.json').read_text())['composition']
 commands=run(['ninja','-C',build,'-t','commands','btx-modeld'],'commands').splitlines()
 cc=[shlex.split(l)for l in commands if l.rstrip().endswith('-c '+str(src/'src/modelnet/s3_store.cpp'))];assert len(cc)==1;cc=cc[0];flags=[];i=1
 while i<len(cc):
  x=cc[i]
  if x in ('-MT','-MF','-o','-c'):i+=2;continue
  if x=='-MD':i+=1;continue
  flags.append(x);i+=1
 link=shlex.split(commands[-1]);assert link[:3]==[':','&&','/usr/bin/g++'] and link[-2:]==['&&',':'];link=link[2:-2]
 obj=w/'clock-consumer.o';binary=w/'clock-consumer';original='src/modelnet/CMakeFiles/btx-modeld.dir/__/modeld.cpp.o';assert link.count(original)==1;link[link.index(original)]=str(obj);link[link.index('-o')+1]=str(binary)
 flag='-Wl,--unresolved-symbols=ignore-in-shared-libs'
 if flag in link:link.remove(flag)
 compile=[cc[0],*flags,'-o',obj,'-c',p/'consumer.cpp'];r['compile']=[str(x)for x in compile];r['link']=[str(x)for x in link]
 run(compile,'compile',build);run(link,'link',build);deps=run(['ldd',binary],'ldd');assert 'not found'not in deps
 raw=run([binary,w/'clock-runtime'],'observation',limit=30);rows=json.loads(raw.splitlines()[-1]);assert len(rows)==4
 assert sum(line.startswith("clock-event ")for line in raw.splitlines())==24
 for row in rows:
  assert len(row['events'])==6
  assert [x['allowed']for x in row['events']][0:2]==[True,False]
  assert row['events'][-1]['allowed']is True and row['events'][-2]['allowed']is False
 r['observations']=rows;r['reproduced_cases']=sum(x['backward_allowed']and x['original_window_allowed_again']for x in rows);r['binary_sha256']=sha(binary);r['consumer_sha256']=sha(p/'consumer.cpp');r['complete']=True
 (out/'observations.json').write_text(json.dumps(rows,indent=2)+'\n')
 assert sha(src/'src/modelnet/s3_store.cpp')==expected
finally:(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
