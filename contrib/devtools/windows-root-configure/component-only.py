from pathlib import Path
import os,sys,json,subprocess,hashlib,shutil
P=Path(__file__).resolve().parent
source=Path(os.environ['GITHUB_WORKSPACE'])/'btx'
e=Path(os.environ['BTX_NATIVE_ROOT'])/'evidence';e.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
config=json.loads((P/'component-inputs.json').read_text())
for name,digest in config['controls'].items():assert sha(P/name)==digest
assert sha(P/'candidate.cpp')==config['candidate_sha256']
assert sha(source/'src/modelnet/capability_runtime.cpp')==config['baseline_sha256']
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==config['source']
subprocess.run(['git','-C',str(source),'diff','--exit-code'],check=True)
result={'source':config['source'],'inputs':config,'scope':'Native CPU/refusal component only; previously proven compiler pair not repeated','components':[]}
result['environment']={k:os.environ.get(k) for k in ['VCToolsVersion','WindowsSDKVersion','ImageVersion']}
result['tools']={name:{'path':shutil.which(name),'sha256':sha(Path(shutil.which(name)))} for name in ['clang-cl','cl']}
assert all(result['tools'][name]['sha256']==digest for name,digest in config['compiler_hashes'].items())
try:
    for compiler in ['clang-cl','cl']:
        out=e/('runtime-component-'+compiler)
        subprocess.run([sys.executable,str(P/'component.py'),str(source),str(out),'candidate',compiler],check=True,timeout=240)
        r=json.loads((out/'receipt.json').read_text());assert r['status']=='PASS'
        result['components'].append({'compiler':compiler,'receipt':str(out/'receipt.json'),'binary_sha256':r['binary_sha256_before_execution']})
    subprocess.run(['git','-C',str(source),'diff','--exit-code'],check=True)
    result['source_unchanged']=True
    result['status']='PASS'
finally:
    (e/'runtime-component-summary.json').write_text(json.dumps(result,indent=2))
