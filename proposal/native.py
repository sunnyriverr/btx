"""Matched actual-helper upload identity/retry test. Controlled HTTP, no wallet/node/peers."""
import argparse,hashlib,json,os,struct,tempfile,time
from pathlib import Path
from origin import Origin
from fixture import Fixture
CHUNK=8<<20
TOTAL=2*CHUNK
OFFSET=CHUNK+4096

def sha(b):return hashlib.sha384(b).hexdigest()
def payload():
 n=TOTAL-128;h=json.dumps({'w':{'dtype':'U8','shape':[n],'data_offsets':[0,n]}},separators=(',',':')).encode();assert len(h)<=120
 return struct.pack('<Q',120)+h.ljust(120,b' ')+b'A'*n

class UploadOrigin(Origin):
 def __init__(self,source,layout,change):
  super().__init__(deadline_seconds=120);self.source=source;self.layout=layout;self.change=change;self.changed=False;self.boundary_seen=False;self.fail_part2=False
 def _handler(self):
  parent=super()._handler();owner=self
  class Handler(parent):
   def _dispatch(self,path,query,body):
    if owner.fail_part2 and self.command=='PUT' and query.get('partNumber')==['2']:
     return 500,b'<Error><Code>InternalError</Code></Error>',None,'injected-part-error'
    answer=super()._dispatch(path,query,body)
    boundary=(answer[3]=='multipart-part' and query.get('partNumber')==['1']) if owner.layout=='SOURCE_FILES' else (answer[3]=='ordinary-put' and path.endswith('/0/0.piece'))
    # A retry can legitimately reach the boundary again; only timed-update cases mutate.
    if boundary and not owner.boundary_seen:
     assert len(body)==(CHUNK if owner.layout=='SOURCE_FILES' else 4<<20)
     owner.boundary_seen=True
     if owner.change:
      with owner.source.open('r+b') as f:
       f.seek(OFFSET);assert f.read(4096)==b'A'*4096;f.seek(OFFSET);f.write(b'B'*4096);f.flush();os.fsync(f.fileno())
      assert owner.source.stat().st_size==TOTAL;owner.changed=True
    return answer
  return Handler

def uploaded(origin,reply,layout):
 art=reply['artifact_id'];keys=[k for k in origin._objects if art in k]
 if layout=='SOURCE_FILES':
  keys=[k for k in keys if '/files/' in k];assert len(keys)==1,keys
 else:
  keys=sorted(k for k in keys if k.endswith('.piece'));assert len(keys)==4,keys
 return b''.join(origin.object_bytes(k) for k in keys)

def configure(f,origin,creds,name,layout):
 cfg={'endpoint':origin.endpoint,'bucket':'fixture','prefix':name,'region':'us-east-1','provider':'GENERIC_S3','layout':layout,'credential_ref':str(creds),'credential_ref_kind':'path','use_fake':False,'allow_http_loopback':True,'automatic_spend_atoms':0,'idempotency_key':name}
 x=f.ok('setcloudstorage',cfg);assert x['applied'] and x['automatic_spend_atoms']==0

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--helper',type=Path,required=True);ap.add_argument('--helper-sha256',required=True);ap.add_argument('--expect',choices=['baseline','candidate'],required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 assert hashlib.sha256(a.helper.read_bytes()).hexdigest()==a.helper_sha256
 a.out.mkdir(parents=True,exist_ok=False);result={'complete':False,'helper_sha256':a.helper_sha256,'phase':a.expect,'cases':{},'scope':__doc__};start=time.monotonic()
 try:
  for layout in ('SOURCE_FILES','PIECE_OBJECTS'):
   for change in (False,True):
    assert time.monotonic()-start<240
    name=layout+('-changed' if change else '-control');out=a.out/name;out.mkdir();c={'complete':False};result['cases'][name]=c
    with tempfile.TemporaryDirectory(prefix='s2-cloud-') as td:
     root=Path(td);source=root/'model.safetensors';original=payload();source.write_bytes(original);f=Fixture(a.helper.resolve(),root,out)
     try:
      with UploadOrigin(source,layout,change) as origin:
       with f.running():
        creds=root/'credentials';creds.write_text('aws_access_key_id=TEST_KEY_NOT_REAL\naws_secret_access_key=TEST_SECRET_NOT_REAL\n');creds.chmod(0o600);configure(f,origin,creds,name,layout)
        reply=f.ok('importmodel',str(source),{'pin':True,'publish':False});assert reply['cloud_uploaded'] is True and reply['automatic_spend_atoms']==0
        assert origin.boundary_seen and origin.changed==change,'mutation boundary not exercised'
        entry=next(x for x in json.loads((f.model/'catalog.json').read_text())['models'] if x['artifact_id']==reply['artifact_id']);assert len(entry['files'])==1 and entry['files'][0]['sha384']==sha(original)
        remote=uploaded(origin,reply,layout);assert len(remote)==TOTAL
        modified=original[:OFFSET]+b'B'*4096+original[OFFSET+4096:]
        expected=modified if change and a.expect=='baseline' else original
        assert remote==expected,(name,'remote payload differs from strict phase expectation')
        c.update(cloud_success=True,imported_sha384=sha(original),remote_sha384=sha(remote),boundary_reached=True,source_changed=origin.changed,identity_matches=(remote==original))
        if layout=='SOURCE_FILES' and not change:
         # Pre-existing good object must survive a later-part failure, then same-ID retry.
         origin.fail_part2=True
         failed=f.ok('importmodel',str(source),{'pin':True,'publish':False})
         assert failed['cloud_uploaded'] is False and failed['artifact_id']==reply['artifact_id'],failed
         assert uploaded(origin,reply,layout)==original and origin.snapshot()['aborted_uploads'] and not origin.snapshot()['uploads']
         origin.fail_part2=False
         retry=f.ok('importmodel',str(source),{'pin':True,'publish':False})
         assert retry['cloud_uploaded'] is True and retry['artifact_id']==reply['artifact_id'] and uploaded(origin,retry,layout)==original
         c['failed_upload_preserves_prior_object']=True;c['same_id_retry']=True
        c['origin']=origin.snapshot()
       c['clean_shutdown']=True
      c['complete']=True
     finally:f.finish();(out/'result.json').write_text(json.dumps(c,indent=2)+'\n')
  result['contract_failures']=[n for n,c in result['cases'].items() if not c['identity_matches']]
  assert len(result['contract_failures'])==(2 if a.expect=='baseline' else 0)
  result['complete']=True
 finally:
  result['seconds']=time.monotonic()-start;(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({n:c['identity_matches'] for n,c in result['cases'].items()}))
 raise SystemExit(2 if result['contract_failures'] else 0)
if __name__=='__main__':main()
