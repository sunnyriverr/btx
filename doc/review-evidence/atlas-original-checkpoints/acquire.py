from pathlib import Path
import urllib.request,json,hashlib,struct,shutil,time
O=Path(__file__).resolve().parent;floor=int(1.25*1024**3)
models=[('pythia-70m','a39f36b100fe8a5377810d56c3f4789b9c53ac42',166029852,'ebfa4e2f18696ebd83716a0d39fe2c025f2ff8483f72a83ca59c475692fc9d15'),('pythia-160m','50f5173d932e8e61f858120bcb800b97af589f46',374998696,'29d2e457a664e41c12c735f20a36dc0956a665f614a54ce5db21a32e75965270')]
records=[]
for name,rev,size,want in models:
 root=O/'models'/name;root.mkdir(parents=True,exist_ok=True)
 assert shutil.disk_usage(O).free>floor+size+10*1024**2
 meta=json.load(urllib.request.urlopen(f'https://huggingface.co/api/models/EleutherAI/{name}/revision/{rev}?blobs=true',timeout=40))
 assert meta['sha']==rev
 (O/(name+'-publisher.json')).write_text(json.dumps(meta,indent=2))
 available={f['rfilename']:f for f in meta['siblings']};rec={'model':name,'revision':rev,'files':{}}
 for fname in ['config.json','tokenizer.json','tokenizer_config.json','special_tokens_map.json','model.safetensors']:
  if fname not in available:continue
  expected=size if fname=='model.safetensors' else available[fname].get('size',10*1024**2)
  assert expected<400*1024**2 and shutil.disk_usage(O).free>floor+expected
  path=root/fname;url=f'https://huggingface.co/EleutherAI/{name}/resolve/{rev}/{fname}'
  h=hashlib.sha256();total=0
  with urllib.request.urlopen(url,timeout=60) as response,path.open('wb') as out:
   while True:
    chunk=response.read(1024**2)
    if not chunk:break
    total+=len(chunk);assert total<=expected
    assert shutil.disk_usage(O).free>floor
    out.write(chunk);h.update(chunk)
  if fname=='model.safetensors':assert total==size and h.hexdigest()==want
  rec['files'][fname]={'bytes':total,'sha256':h.hexdigest(),'url':url}
 with (root/'model.safetensors').open('rb') as f:
  length=struct.unpack('<Q',f.read(8))[0];assert length<1024**2;header=json.loads(f.read(length))
 keys=[k for k in header if k!='__metadata__'];buffers=[k for k in keys if k.endswith(('.attention.bias','.attention.masked_bias','.attention.rotary_emb.inv_freq'))];assert buffers
 rec.update(tensors=len(keys),legacy_buffers=buffers,free_disk_bytes=shutil.disk_usage(O).free);records.append(rec)
 (O/'checkpoints.json').write_text(json.dumps(records,indent=2));print(name,len(keys),'tensors',len(buffers),'legacy buffers verified',flush=True)
