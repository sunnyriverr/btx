"""Bootstrap the exact existing vcpkg tool via official asset API; no project build."""
from pathlib import Path
import sys,hashlib,urllib.request,datetime,json,os
RUNNER_SHA='73fea130e528e1034d508ec2ff1da76d710074792dc1af618ccb3a499e2f3f8b'
P=Path(__file__).resolve().parent
original=P/'runner.py'
assert hashlib.sha256(original.read_bytes()).hexdigest()==RUNNER_SHA
text=original.read_text();prefix,sep,suffix=text.partition('stage=sys.argv[1];failed=False');assert sep
ns={'__file__':str(original),'__name__':'btx_pinned_bootstrap'}
exec(compile(prefix,str(original),'exec'),ns)
def pinned_bootstrap():
 tool=ns['ROOT']/'vcpkg';need=ns['need'];result=ns['result']
 if not(tool/'.git').exists():need('vcpkg-clone',['git','clone','--no-checkout','https://github.com/microsoft/vcpkg.git',str(tool)],timeout=240)
 need('vcpkg-checkout',['git','-C',str(tool),'checkout','--detach',ns['VCPKG_COMMIT']],timeout=120)
 head=ns['subprocess'].check_output(['git','-C',str(tool),'rev-parse','HEAD'],text=True).strip();assert head==ns['VCPKG_COMMIT']
 assert 'VCPKG_TOOL_RELEASE_TAG=2026-10-29' in (tool/'scripts/vcpkg-tool-metadata.txt').read_text()
 url='https://api.github.com/repos/microsoft/vcpkg-tool/releases/assets/690264732'
 request=urllib.request.Request(url,headers={'Accept':'application/octet-stream','User-Agent':'btx-pinned-native-tool','X-GitHub-Api-Version':'2022-11-28'})
 with urllib.request.urlopen(request,timeout=90)as response:
  data=response.read(10*1024*1024);assert response.status==200
 digest=hashlib.sha256(data).hexdigest();assert len(data)==6836024 and digest=='191ee64b0887af80aad3eff6c5e888ab733d3ef2182885ed4747b4574c201834'
 part=tool/'vcpkg.exe.part';part.write_bytes(data);assert ns['sha'](part)==digest;os.replace(part,tool/'vcpkg.exe')
 (tool/'vcpkg.disable-metrics').write_text('')
 need('vcpkg-version',[str(tool/'vcpkg.exe'),'version'])
 result['vcpkg_commit']=head;result['vcpkg_executable_sha256']=digest
 result['vcpkg_bootstrap_method']={'method':'official_release_asset_API','url':url,'bytes':len(data),'sha256':digest,'matches_previous_successful_executable':True,'helper_sha256':ns['sha'](Path(__file__)),'original_runner_unchanged_sha256':RUNNER_SHA,'project_compilation':False}
 (ns['E']/'vcpkg-asset-route.json').write_text(json.dumps(result['vcpkg_bootstrap_method'],indent=2)+'\n')
 promisor=ns['subprocess'].run(['git','-C',str(tool),'config','--get','remote.origin.promisor'],capture_output=True,text=True);result['vcpkg_promisor_remote']=promisor.stdout.strip();assert promisor.stdout.strip().lower()!='true'
 for oid in ['8ed2f86ee404263f5aa1f72f8f4f13ee44262b81','937a2198387cb5c913e4feea170652651dd756ba']:
  need('vcpkg-historical-blob-'+oid[:8],['git','-C',str(tool),'cat-file','-e',oid],timeout=30)
ns['vcpkg']=pinned_bootstrap
# Run the original stage dispatcher and source verification with real command outcomes.
exec(compile(sep+suffix,str(original),'exec'),ns)
