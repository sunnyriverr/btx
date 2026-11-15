from pathlib import Path
import os,sys,json,hashlib,subprocess,shlex
R=Path('D:/btx-native-035');B=R/'project-build';S=Path(os.environ['GITHUB_WORKSPACE'])/'btx';E=R/'ensure-controls-evidence';E.mkdir(parents=True);F=Path(__file__).parent
result={'source':'61f13b8870ed98c7b10db2e32c04fb647023f4ef','product_object_compile_reused':43712374900}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save():(E/'result.json').write_text(json.dumps(result,indent=2))
def run(name,args):
 p=subprocess.run(args,cwd=B,capture_output=True,timeout=120);(E/(name+'.log')).write_bytes(p.stdout+p.stderr);print(name,p.returncode,(p.stdout+p.stderr).decode(errors='replace')[-1800:],flush=True);result.setdefault('commands',[]).append({'name':name,'exit':p.returncode});save();p.check_returncode()
try:
 assert sha(B/'btx-successor.json')=='098f12ce453d1c32319fa9e4a1712caea99204635d18ded151a391d0823e53f6';cp=json.loads((B/'btx-successor.json').read_text());assert cp['source']==result['source']
 for n,v in cp['files'].items():assert sha(R/n)==v['sha256'],n
 result['verified_files']=len(cp['files']);shutil=__import__('shutil');shutil.copyfile(F/'capability_ensure.fixed.cpp',S/'src/modelnet/capability_ensure.cpp')
 for n,v in cp['source_files'].items():assert sha(S/n)==v['sha256'],n
 obj=E/'controls.obj';exe=E/'controls.exe';run('controls-compile',['clang-cl','/nologo','/std:c++20','/EHsc','/MT','/O2','/I'+str(S/'src'),'/I'+str(B/'src'),'/I'+str(S/'src/univalue/include'),'/I'+str(R/'vcpkg-installed/x64-windows-static/include'),'/c',str(F/'ensure-private-dir-controls-diagnostic.cpp'),'/Fo'+str(obj)])
 block=(B/'build.ninja').read_text().split('build bin/btx-security.exe:',1)[1];libs=next(l.split(' = ',1)[1] for l in block.splitlines() if l.startswith('  LINK_LIBRARIES = '));args=[x.strip('"') for x in shlex.split(libs,posix=False)];run('controls-link',['lld-link','/machine:x64','/subsystem:console','/OUT:'+str(exe),str(obj)]+args);run('controls-runtime',[str(exe),str(E/'native-private-dir-fixture')]);result['status']='NATIVE_CONTROLS_PASS'
except Exception as e:result['status']='NATIVE_CONTROLS_FAILED';result['error']=repr(e);raise
finally:save()
