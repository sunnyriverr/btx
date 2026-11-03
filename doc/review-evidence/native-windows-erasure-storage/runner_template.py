from pathlib import Path
import os,sys,subprocess,base64,json,hashlib,platform,shutil
PAYLOAD = None
def main():
 root=Path(sys.argv[1]).resolve();root.mkdir(parents=True,exist_ok=False)
 result={'platform':platform.platform(),'native_windows':os.name=='nt','toolset':os.environ.get('VCToolsVersion'),'sdk':os.environ.get('WindowsSDKVersion'),'commands':[],'errors':[],'files':{}}
 def run(label,cmd,cwd):
  p=subprocess.run([str(x)for x in cmd],cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
  log=p.stdout;(root/(label+'.log')).write_bytes(log)
  result['commands'].append({'label':label,'command':[str(x)for x in cmd],'exit':p.returncode,'log_sha256':hashlib.sha256(log).hexdigest()})
  print(label,p.returncode,log.decode(errors='replace')[-3000:],flush=True);return p
 compilers=['cl','clang-cl']if os.name=='nt'else['clang++']
 for cc in compilers:
  run(cc+'-version',[cc,'/Bv']if cc=='cl'else[cc,'--version'],root)
  for variant in ['baseline','header-only','candidate']:
   if os.name!='nt'and variant=='header-only':continue
   d=root/(cc+'-'+variant);d.mkdir()
   for f,b in PAYLOAD['files'].items():
    data=base64.b64decode(b)
    if f=='src/modelnet/erasure_store.cpp'and variant!='baseline':data=base64.b64decode(PAYLOAD['candidate'])
    if f=='src/modelnet/erasure_store.cpp'and variant=='header-only':data=data.replace(b'    flags |= _O_BINARY;',b'    // Diagnostic control: preserve the old Windows text mode.')
    q=d/f;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(data)
    result['files'][cc+'-'+variant+':'+f]=hashlib.sha256(data).hexdigest()
   test=d/'storage_test.cpp';test.write_bytes(base64.b64decode(PAYLOAD['test']))
   sources=[d/f for f in PAYLOAD['cpps']]+[test];exe=d/('storage_test.exe'if os.name=='nt'else'storage_test')
   if os.name=='nt':
    flags=['/nologo','/std:c++20','/EHsc','/O2','/Gy','/MT','/DWIN32','/D_WIN32_WINNT=0x0A00','/DWIN32_LEAN_AND_MEAN','/DNOMINMAX','/D_CRT_SECURE_NO_WARNINGS','/I'+str(d/'src'),'/I'+str(d/'src/univalue/include'),'/FI'+str(d/'src/compat/mingw/posix_extra.h')]
    cmd=[cc,*flags,*sources,'/Fe:'+str(exe),'/link','/OPT:REF']
   else:cmd=[cc,'-std=c++20','-O2','-I'+str(d/'src'),'-I'+str(d/'src/univalue/include'),*sources,'-o',exe]
   p=run(cc+'-'+variant+'-build',cmd,d)
   if variant=='baseline'and os.name=='nt':
    if p.returncode==0 or b'unistd.h'not in p.stdout:result['errors'].append(cc+' baseline signature')
    continue
   if p.returncode!=0:result['errors'].append(cc+' '+variant+' build');continue
   p=run(cc+'-'+variant+'-runtime',[exe,d/'fixture'],d)
   if variant=='header-only':
    if p.returncode==0 or b'FAIL binary bytes preserved'not in p.stdout:result['errors'].append(cc+' text-mode control signature')
   elif p.returncode!=0:result['errors'].append(cc+' '+variant+' runtime')
 (root/'result.json').write_text(json.dumps(result,indent=2));return bool(result['errors'])
if __name__=='__main__':raise SystemExit(main())
