from pathlib import Path
import subprocess,concurrent.futures,json,hashlib
r=Path(__file__).resolve().parent;m=json.loads((r/'manifest.json').read_text());b=r/'build';b.mkdir(exist_ok=True)
includes=['-I'+str(r/d) for d in ['src','src/univalue/include','src/libbitcoinpqc/include','src/libbitcoinpqc/dilithium/ref']]
def run(cmd):subprocess.run(cmd,check=True,timeout=180)
def compile(p):
 obj=b/(p.replace('/','_')+'.o');args=['cc','-std=c11','-DDILITHIUM_MODE=2','-DCUSTOM_RANDOMBYTES=1','-Drandombytes=btx_mldsa_randombytes'] if p.endswith('.c') else ['c++','-std=c++20']
 run(args+['-O1','-ffunction-sections','-fdata-sections',*includes,'-c',str(r/p),'-o',str(obj)]);return str(obj)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:objects=list(pool.map(compile,m['cpp_sources']+m['c_sources']))
obj=compile('src/modelnet/native_qualification_main.cpp');run(['c++','-Wl,--gc-sections',obj,*objects,'-pthread','-o',str(b/'btx-native-qualify')])
for mb in [8,96]:run(['cc','-std=c11','-O2','-static','-DPROBE_MB='+str(mb),str(r/'probe.c'),'-o',str(b/('probe'+str(mb)))])
print('BINARY_SHA256',hashlib.sha256((b/'btx-native-qualify').read_bytes()).hexdigest(),flush=True)
