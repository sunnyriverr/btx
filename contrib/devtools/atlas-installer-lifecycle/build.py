"""Build the exact Atlas package without source/configuration changes."""
from pathlib import Path
import hashlib,json,os,platform,re,shutil,subprocess,sys,time,urllib.request,zipfile
HERE=Path(__file__).resolve().parent
OUT=Path('atlas-installer-results').resolve();OUT.mkdir(exist_ok=True)
PRODUCT=Path('atlas-product').resolve()
RETAIN=Path('atlas-package-output').resolve();RETAIN.mkdir(exist_ok=True)
STATE={'platform':platform.platform(),'commands':[],'checks':[],'errors':[]}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check(name,okay):
 STATE['checks'].append({'name':name,'pass':bool(okay)})
 if not okay:raise RuntimeError(name)
def cmd(args,name,cwd=None,env=None,timeout=120):
 start=time.monotonic()
 with (OUT/(name+'.log')).open('wb') as log:r=subprocess.run(list(map(str,args)),cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
 STATE['commands'].append({'args':list(map(str,args)),'cwd':str(cwd),'exit':r.returncode,'seconds':round(time.monotonic()-start,2),'log':name+'.log'})
 check(name+' exit',r.returncode==0)
def source_check(manifest,label):
 for item in manifest['files']:check(label+' '+item['path'],sha(PRODUCT/item['path'])==item['sha256'])
def main():
 check('native Windows',sys.platform=='win32')
 manifest=json.loads((HERE/'inputs.json').read_text());STATE['inputs']=manifest
 for name,digest in manifest['fixtures'].items():check('fixture '+name,sha(HERE/name)==digest)
 src=json.loads((HERE/'product-inputs.json').read_text());head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=PRODUCT,text=True).strip()
 check('exact product revision',head==src['source']);source_check(src,'before')
 config=json.loads((PRODUCT/'gui/atlas/src-tauri/tauri.conf.json').read_text());check('offline config unchanged',config['bundle']['windows']['webviewInstallMode']['type']=='offlineInstaller');STATE['effective_source_config']=config
 tool=Path(os.environ['RUNNER_TEMP'])/'atlas-cli-package';tool.mkdir();archive=tool/'cli.zip'
 with urllib.request.urlopen(manifest['cli']['url'],timeout=90) as response:archive.write_bytes(response.read())
 check('CLI archive digest',sha(archive)==manifest['cli']['sha256'])
 with zipfile.ZipFile(archive) as z:
  check('CLI archive bounded',sum(i.file_size for i in z.infolist())<100_000_000)
  check('CLI archive paths',all(not Path(i.filename).is_absolute() and '..' not in Path(i.filename).parts for i in z.infolist()));z.extractall(tool)
 cli=list(tool.rglob('cargo-tauri.exe'));check('one CLI binary',len(cli)==1);STATE['cli_binary_sha256']=sha(cli[0])
 env=dict(os.environ,PATH=str(cli[0].parent)+os.pathsep+os.environ['PATH'],CARGO_TARGET_DIR=str(Path(os.environ['RUNNER_TEMP'])/'atlas-package-target'))
 cmd(['rustup','toolchain','install','1.95.0','--profile','minimal'],'rust-install',env=env,timeout=300)
 cmd(['rustc','+1.95.0','-Vv'],'rust-version',env=env);cmd(['cargo','+1.95.0','tauri','--version'],'cli-version',env=env)
 cmd(['cargo','+1.95.0','tauri','build','--ci','--bundles','nsis','--','--locked'],'package-build',cwd=PRODUCT/'gui/atlas',env=env,timeout=1800)
 target=Path(env['CARGO_TARGET_DIR']);installers=list(target.glob('release/bundle/nsis/*.exe'));check('one real NSIS bundle',len(installers)==1)
 binary=target/'release/btx-atlas.exe';check('built Atlas executable exists',binary.is_file())
 retained=RETAIN/installers[0].name;shutil.copyfile(installers[0],retained)
 STATE['built_package_raw']={'installer_path':str(retained),'installer_sha256':sha(retained),'binary_path':str(binary),'binary_sha256':sha(binary)}
 scripts=list(target.rglob('installer.nsi'));check('one generated NSIS script',len(scripts)==1)
 generated=scripts[0].read_text(encoding='utf-8-sig');definitions=dict(re.findall(r'^!define\s+(\w+)\s+"(.*)"\s*$',generated,re.M))
 check('generated per-user mode',definitions.get('INSTALLMODE')=='currentUser');check('generated offline WebView',definitions.get('INSTALLWEBVIEW2MODE')=='offlineInstaller')
 check('generated real btx association','APP_ASSOCIATE "btx" "BTX Model Resource"' in generated);check('generated unassociation','APP_UNASSOCIATE "btx" "BTX Model Resource"' in generated)
 for name in ['installer.nsi','FileAssociation.nsh','utils.nsh']:
  f=scripts[0].parent/name;check('generated '+name,f.is_file());shutil.copyfile(f,OUT/('generated-'+name))
 raw_macro=(OUT/'generated-FileAssociation.nsh').read_bytes()
 # The bundler writes its included macro bytes with a UTF-8 BOM; retain raw bytes.
 macro_content=raw_macro[3:] if raw_macro.startswith(b'\xef\xbb\xbf') else raw_macro
 check('actual dependency macro content unchanged',hashlib.sha256(macro_content).hexdigest()==manifest['macro_sha256'])
 STATE['generated_macro']={'raw_sha256':hashlib.sha256(raw_macro).hexdigest(),'content_sha256':hashlib.sha256(macro_content).hexdigest(),'utf8_bom':raw_macro.startswith(b'\xef\xbb\xbf')}
 payload=Path(definitions['WEBVIEW2INSTALLERPATH']);check('offline payload exists',payload.is_file())
 STATE['package']={'installer_path':str(retained),'installer_sha256':sha(retained),'installer_size':retained.stat().st_size,'binary_path':str(binary),'binary_sha256':sha(binary),'payload_path':str(payload),'payload_sha256':sha(payload),'payload_size':payload.stat().st_size,'definitions':definitions,'source':head,'config_sha256':sha(PRODUCT/'gui/atlas/src-tauri/tauri.conf.json'),'lock_sha256':sha(PRODUCT/'gui/atlas/Cargo.lock')}
 source_check(src,'after');shutil.rmtree(tool)
try:main()
except Exception as exc:STATE['errors'].append(repr(exc))
finally:
 STATE['pass']=not STATE['errors'] and bool(STATE['checks']) and all(x['pass'] for x in STATE['checks']);(OUT/'build.json').write_text(json.dumps(STATE,indent=2)+'\n');print(json.dumps({'pass':STATE['pass'],'errors':STATE['errors'],'package':STATE.get('package')},indent=2))
sys.exit(0 if STATE['pass'] else 1)
