"""Bundle repaired installer using hash-verified original application bytes."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys,time,urllib.request,zipfile
HERE=Path(__file__).resolve().parent
OUT=Path('atlas-installer-results').resolve();OUT.mkdir(exist_ok=True)
PRODUCT=Path('atlas-product').resolve();RETAIN=Path('atlas-candidate-package').resolve();RETAIN.mkdir(exist_ok=True)
STATE={'checks':[],'commands':[],'errors':[]}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check(name,okay):
 STATE['checks'].append({'name':name,'pass':bool(okay)})
 if not okay:raise RuntimeError(name)
def cmd(args,name,cwd=None,env=None,timeout=120):
 start=time.monotonic()
 with (OUT/(name+'.log')).open('wb') as f:r=subprocess.run(list(map(str,args)),cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
 STATE['commands'].append({'args':list(map(str,args)),'cwd':str(cwd),'exit':r.returncode,'seconds':round(time.monotonic()-start,2),'log':name+'.log'});check(name,r.returncode==0)
def audit(catalog,label):
 for f in catalog['files']:check(label+' '+f['path'],sha(PRODUCT/f['path'])==f['sha256'])
def main():
 m=json.loads((HERE/'inputs.json').read_text());STATE['inputs']=m
 for n,h in m['fixtures'].items():check('fixture '+n,sha(HERE/n)==h)
 check('base checkout',subprocess.check_output(['git','rev-parse','HEAD'],cwd=PRODUCT,text=True).strip()==m['base'])
 cmd(['git','apply','--check',str(HERE/'product.patch')],'patch-check',cwd=PRODUCT);cmd(['git','apply',str(HERE/'product.patch')],'patch-apply',cwd=PRODUCT)
 cmd(['git','add','--sparse','--','gui/atlas'],'stage-product',cwd=PRODUCT);check('candidate tree',subprocess.check_output(['git','write-tree'],cwd=PRODUCT,text=True).strip()==m['product_tree'])
 catalog=json.loads((HERE/'product-inputs.json').read_text());audit(catalog,'before')
 baseline=next(Path('baseline-package').resolve().glob('*.exe'));check('baseline installer hash',sha(baseline)==m['baseline_installer_sha256'])
 seven=shutil.which('7z') or str(Path(os.environ['ProgramFiles'])/'7-Zip/7z.exe');check('extractor exists',Path(seven).is_file())
 extract=Path(os.environ['RUNNER_TEMP'])/'atlas-repackage-inputs';extract.mkdir();cmd([seven,'l','-slt',baseline],'baseline-list')
 entries=[s.rstrip('\r') for s in re.findall(r'^Path = (.+)\r?$',(OUT/'baseline-list.log').read_text(errors='replace'),re.M)]
 app=[e for e in entries if Path(e).name=='btx-atlas.exe'];wv=[e for e in entries if Path(e).name=='MicrosoftEdgeWebView2RuntimeInstaller.exe'];check('unique assets',len(app)==len(wv)==1)
 cmd([seven,'e','-y','-o'+str(extract),baseline,app[0],wv[0]],'extract-original-assets')
 embedded=extract/'btx-atlas.exe';check('embedded app hash',sha(embedded)==m['baseline_embedded_sha256']);b=embedded.read_bytes();nss=b'__TAURI_BUNDLE_TYPE_VAR_NSS';unk=b'__TAURI_BUNDLE_TYPE_VAR_UNK';check('unique NSIS marker',b.count(nss)==1)
 restored=b.replace(nss,unk,1);check('restored compiled app',hashlib.sha256(restored).hexdigest()==m['restored_app_sha256'])
 target=Path(os.environ['RUNNER_TEMP'])/'atlas-candidate-target';release=target/'release';release.mkdir(parents=True);binary=release/'btx-atlas.exe';binary.write_bytes(restored)
 old=dict(re.findall(r'^!define\s+(\w+)\s+"(.*)"\s*$',(HERE/'original-installer.nsi').read_text(encoding='utf-8-sig'),re.M));tail=Path(old['WEBVIEW2INSTALLERPATH']).parts;idx=next(i for i,x in enumerate(tail) if x.lower()=='tauri')
 cache=Path(os.environ['LOCALAPPDATA']).joinpath(*tail[idx:]);cache.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(extract/'MicrosoftEdgeWebView2RuntimeInstaller.exe',cache);runtime_sha=sha(cache)
 STATE['reused_assets']={'baseline_installer_sha256':sha(baseline),'baseline_embedded_sha256':sha(embedded),'restored_app_sha256':sha(binary),'runtime_sha256':runtime_sha,'binary_recompiled':False}
 tool=Path(os.environ['RUNNER_TEMP'])/'atlas-repair-cli';tool.mkdir();archive=tool/'cli.zip'
 with urllib.request.urlopen(m['cli']['url'],timeout=90) as z:archive.write_bytes(z.read())
 check('CLI archive hash',sha(archive)==m['cli']['sha256'])
 with zipfile.ZipFile(archive) as z:
  check('CLI archive bounded',sum(x.file_size for x in z.infolist())<100_000_000 and all(not Path(x.filename).is_absolute() and '..' not in Path(x.filename).parts for x in z.infolist()));z.extractall(tool)
 cli=list(tool.rglob('cargo-tauri.exe'));check('one CLI',len(cli)==1)
 env=dict(os.environ,PATH=str(cli[0].parent)+os.pathsep+os.environ['PATH'],CARGO_TARGET_DIR=str(target))
 cmd(['rustup','toolchain','install','1.95.0','--profile','minimal'],'rust-install',env=env,timeout=300);cmd(['cargo','+1.95.0','tauri','--version'],'cli-version',env=env)
 cmd(['cargo','+1.95.0','tauri','bundle','--ci','--bundles','nsis'],'candidate-bundle',cwd=PRODUCT/'gui/atlas',env=env,timeout=600)
 check('restored app unchanged after bundle',sha(binary)==m['restored_app_sha256'])
 installers=list(release.glob('bundle/nsis/*.exe'));check('one candidate installer',len(installers)==1);candidate=RETAIN/installers[0].name;shutil.copyfile(installers[0],candidate)
 scripts=list(target.rglob('installer.nsi'));check('one generated script',len(scripts)==1);generated=scripts[0].read_text(encoding='utf-8-sig');defs=dict(re.findall(r'^!define\s+(\w+)\s+"(.*)"\s*$',generated,re.M));hook=PRODUCT/'gui/atlas/src-tauri/windows/association-hooks.nsh'
 check('real hook included after default macros',str(hook) in generated and generated.index('!include "FileAssociation.nsh"')<generated.index(str(hook)))
 check('same per-user/offline mode',defs['INSTALLMODE']=='currentUser' and defs['INSTALLWEBVIEW2MODE']=='offlineInstaller');check('same prerequisite bytes',sha(Path(defs['WEBVIEW2INSTALLERPATH']))==runtime_sha)
 shutil.copyfile(scripts[0],OUT/'candidate-installer.nsi');shutil.copyfile(hook,OUT/'candidate-association-hooks.nsh')
 cmd([seven,'e','-y','-o'+str(extract/'candidate'),candidate,'btx-atlas.exe'],'extract-candidate-app');check('candidate payload unchanged',sha(extract/'candidate/btx-atlas.exe')==m['baseline_embedded_sha256']);audit(catalog,'after')
 package={'installer_path':str(candidate),'installer_sha256':sha(candidate),'binary_sha256':m['baseline_embedded_sha256'],'definitions':defs,'source':m['product_head']}
 q={'qualified_for_lifecycle_test':True,'package':package,'facts':{'candidate_commit':m['product_head'],'candidate_tree':m['product_tree'],'base':m['base'],'app_recompiled':False,'app_payload_unchanged':True,'offline_prerequisite_hash':runtime_sha,'source_before_after_audited':True},'inputs':m}
 (OUT/'qualification.json').write_text(json.dumps(q,indent=2)+'\n');shutil.rmtree(extract);shutil.rmtree(tool)
try:main()
except Exception as e:STATE['errors'].append(repr(e))
finally:
 STATE['pass']=bool(STATE['checks']) and all(x['pass'] for x in STATE['checks']) and not STATE['errors'];(OUT/'bundle.json').write_text(json.dumps(STATE,indent=2)+'\n');print(json.dumps({'pass':STATE['pass'],'errors':STATE['errors']},indent=2))
sys.exit(0 if STATE['pass'] else 1)
