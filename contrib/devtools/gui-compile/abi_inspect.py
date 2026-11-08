from pathlib import Path
import importlib.util,sys,json,hashlib,re
def inspect_binary(binary,out,state,run):
 path=Path(__file__).with_name('verify_release_btxd.py');spec=importlib.util.spec_from_file_location('existing_abi',path);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
 text=run(['ldd',binary],'component-ldd');assert 'not found' not in text,'Unresolved runtime dependency'
 files=[binary]
 for line in text.splitlines():
  match=re.search(r'=>\s+(/\S+)',line)
  if match and Path(match[1]).is_file():files.append(Path(match[1]))
 inventory=[{'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'versions':m.elf_required_versions(f)} for f in dict.fromkeys(files)]
 state['abi_inventory']=inventory;state['glibc_offenders']=[x for x in inventory if x['versions'].get('GLIBC') and m.version_key(x['versions']['GLIBC'])>m.version_key('2.38')]
 state['abi_pass']=not state['glibc_offenders']
 (out/'abi.json').write_text(json.dumps({'glibc_ceiling':'2.38','inventory':inventory,'pass':state['abi_pass']},indent=2)+'\n')
 assert state['abi_pass'],'Component/dependency GLIBC floor above2.38'
