import hashlib,json,locale,os,re,subprocess,sys,time,urllib.request
from pathlib import Path
START=time.monotonic(); ROOT=Path.cwd(); OUT=ROOT/'probe-results';OUT.mkdir(exist_ok=True)
BASE='1e2f8b5f12295002334d3390c12cac0bb4ae2aff'; TARGET='371013d61dc124a363521df5b94e97f64d2464f2'
def sha(b):return hashlib.sha256(b).hexdigest()
def run(args,log,timeout=90):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
 (OUT/log).write_bytes(p.stdout);return p
record={'target':TARGET,'old_generator_revision':BASE,'python':sys.version,'encoding':locale.getpreferredencoding(False),'platform':sys.platform,'profile':['/std:c++20','/utf-8','/EHsc','/O2','/MD','/Zc:__cplusplus'],'cases':{}}
try:
 assert sys.platform=='win32'
 vswhere=Path(os.environ['ProgramFiles(x86)'])/'Microsoft Visual Studio/Installer/vswhere.exe'
 install=subprocess.check_output([str(vswhere),'-latest','-products','*','-requires','Microsoft.VisualStudio.Component.VC.Tools.x86.x64','-property','installationPath'],text=True).strip()
 assert install,'No native MSVC installation'
 dev=Path(install)/'Common7/Tools/VsDevCmd.bat';assert dev.is_file()
 env=subprocess.check_output(f'call "{dev}" -arch=x64 -host_arch=x64 >nul && set',shell=True,text=True)
 for line in env.splitlines():
  if '=' in line and not line.startswith('='):
   k,v=line.split('=',1);os.environ[k]=v
 record['visual_studio']=install;record['vctools_version']=os.environ.get('VCToolsVersion');record['sdk_version']=os.environ.get('WindowsSDKVersion')
 pre=run(['cl.exe'], 'compiler.txt');record['compiler_output']=pre.stdout.decode(errors='replace')
 assert b'Microsoft' in pre.stdout and b'x64' in pre.stdout,record['compiler_output']
 current=ROOT/'contrib/swapnet/generate_embedded.py';source=ROOT/'contrib/swapnet/swapnet'
 old=OUT/'old_generate_embedded.py'
 old.write_bytes(urllib.request.urlopen(f'https://raw.githubusercontent.com/btxchain/btx/{BASE}/contrib/swapnet/generate_embedded.py',timeout=30).read())
 record['generators']={'old':sha(old.read_bytes()),'new':sha(current.read_bytes())}
 record['source_files']={p.name:sha(p.read_bytes()) for p in sorted(source.glob('*.py')) if p.stem!='runtime'}
 payloads={}
 for label,generator in [('before',old),('after',current)]:
  d=OUT/label;d.mkdir();header=d/'embedded.h'
  gen=run([sys.executable,str(generator),str(source),str(header)],f'{label}-generate.log')
  assert gen.returncode==0,f'{label} generator failed'
  text=header.read_text();parts=re.findall(r'R"(SN[0-9a-f]{12})\((.*?)\)\1"',text,re.S)
  assert parts,'No raw literal found';payload=''.join(s for _,s in parts).encode('utf-8');payloads[label]=payload
  record['cases'][label]={'header_sha256':sha(header.read_bytes()),'payload_sha256':sha(payload),'payload_bytes':len(payload),'literal_count':len(parts),'max_literal_characters':max(len(s) for _,s in parts)}
  (d/'expected.bin').write_bytes(payload)
 assert payloads['before']==payloads['after'],'Generator payload mismatch before compiler'
 consumer='#include "embedded.h"\n#include <cstring>\n#include <fstream>\nint main(int argc,char**argv){if(argc!=2)return 2;std::ofstream out(argv[1],std::ios::binary);out.write(swapnet::FROZEN_BOOTSTRAP,std::strlen(swapnet::FROZEN_BOOTSTRAP));out.close();return out.fail()?3:0;}\n'
 for label in ['before','after']:
  d=OUT/label;(d/'consumer.cpp').write_text(consumer,encoding='utf-8');exe=d/'consumer.exe'
  args=['cl.exe','/nologo',*record['profile'],str(d/'consumer.cpp'),'/Fo'+str(d/'consumer.obj'),'/Fe'+str(exe)]
  record['cases'][label]['command']=args
  compiled=run(args,f'{label}-compile.log',120);record['cases'][label]['compile_exit']=compiled.returncode
  if compiled.returncode==0:
   output=d/'actual.bin';executed=run([str(exe),str(output)],f'{label}-execute.log')
   record['cases'][label].update(execute_exit=executed.returncode,actual_sha256=sha(output.read_bytes()),exact_payload=output.read_bytes()==payloads[label])
   assert executed.returncode==0 and record['cases'][label]['exact_payload']
  else:
   record['cases'][label]['diagnostic']=compiled.stdout.decode(errors='replace')[-12000:]
 record['before_expected_literal_failure']=record['cases']['before']['compile_exit']!=0 and any(c in record['cases']['before'].get('diagnostic','') for c in ['C2026','C1091','C2117'])
 record['after_pass']=record['cases']['after'].get('exact_payload',False)
 record['verdict']='PASS' if record['before_expected_literal_failure'] and record['after_pass'] else 'COMPILER_RESULT_REQUIRES_CLASSIFICATION'
except Exception as e:
 record['verdict']='SETUP_OR_PROBE_FAILURE';record['error']=repr(e)
finally:
 record['elapsed_seconds']=round(time.monotonic()-START,3)
 (OUT/'result.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record,indent=2))
 # Preserve bounded unexpected native diagnostics as results, not a misleading pass.
 sys.exit(0 if record.get('verdict')=='PASS' else 1)
