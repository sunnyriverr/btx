from pathlib import Path
import os,sys,subprocess,json,platform,shutil
p=Path(os.environ['GITHUB_WORKSPACE'])/'mac-toolchain-records';p.mkdir(exist_ok=True);r={'machine':platform.machine(),'image_version':os.getenv('ImageVersion'),'image_os':os.getenv('ImageOS'),'installs':False,'btx_build':False,'commands':[]}
def cmd(argv,label,env=None,limit=30):
 try:
  x=subprocess.run(argv,env=env,capture_output=True,text=True,timeout=limit);d={'label':label,'args':argv,'exit':x.returncode,'output':x.stdout+x.stderr}
 except (OSError,subprocess.TimeoutExpired) as e:d={'label':label,'args':argv,'exit':None,'error':str(e)}
 r['commands'].append(d);return d
cmd(['sw_vers'],'os');cmd(['xcode-select','-p'],'selected-developer');cmd(['df','-h','.'],'disk');cmd(['sysctl','-n','hw.memsize'],'memory');cmd(['brew','list','--versions'],'installed-brew')
for tool in ['cmake','ninja','pkg-config','rustc','cargo','openssl','codesign']:
 r.setdefault('tools',{})[tool]=shutil.which(tool)
 if r['tools'][tool] and tool not in ['codesign']:cmd([r['tools'][tool],'version' if tool=='openssl' else '--version'],'version-'+tool)
source=p/'probe.metal';source.write_text('#include <metal_stdlib>\nusing namespace metal;\nkernel void readiness(device uint* out [[buffer(0)]], uint tid [[thread_position_in_grid]]) { out[tid] = tid; }\n')
paths=[None]+[str(x/'Contents/Developer') for x in sorted(Path('/Applications').glob('Xcode*.app'),reverse=True)][:4];r['metal_candidates']=[]
for i,path in enumerate(paths):
 env=dict(os.environ)
 if path:env['DEVELOPER_DIR']=path
 item={'developer_dir':path or 'selected'};r['metal_candidates'].append(item)
 for name in ['metal','metallib']:
  v=cmd(['xcrun','--find',name],str(i)+'-find-'+name,env);item[name]=v['exit']==0
 if not(item['metal'] and item['metallib']):continue
 cmd(['xcodebuild','-version'],str(i)+'-xcode-version',env);cmd(['xcrun','--sdk','macosx','--show-sdk-version'],str(i)+'-sdk',env)
 compile=cmd(['xcrun','--sdk','macosx','metal','-c',str(source),'-o',str(p/'probe.air')],str(i)+'-basic-compile',env)
 link=cmd(['xcrun','--sdk','macosx','metallib',str(p/'probe.air'),'-o',str(p/'probe.metallib')],str(i)+'-basic-link',env) if compile['exit']==0 else {'exit':None}
 item['basic_pass']=compile['exit']==0 and link['exit']==0
 if item['basic_pass']:
  item['metal4_compile']=cmd(['xcrun','--sdk','macosx','metal','-std=metal4.0','-c',str(source),'-o',str(p/'probe4.air')],str(i)+'-metal4-compile',env)['exit']==0
  break
r['basic_metal_available']=any(x.get('basic_pass') for x in r['metal_candidates']);r['supported_arm_host']=r['machine']=='arm64';(p/'result.json').write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items() if k!='commands'},indent=2))
# Diagnostic completes even when compiler admission is blocked; the explicit field is the verdict.
sys.exit(0)
