"""Two small actual-helper imports against a controlled loopback S3 origin.
Not MinIO/AWS, not a restore test, and no signature-validation claim.
"""
import argparse,hashlib,json,os,shutil,struct,tempfile,time
from pathlib import Path
from origin import Origin
from fixture import Fixture
from check import classify

CHUNK=8<<20
TOTAL=2*CHUNK
OFFSET=CHUNK+4096

def sha(blob): return hashlib.sha384(blob).hexdigest()

def payload():
    n=TOTAL-128
    header=json.dumps({'w':{'dtype':'U8','shape':[n],'data_offsets':[0,n]}},separators=(',',':')).encode()
    assert len(header)<=120
    return struct.pack('<Q',120)+header.ljust(120,b' ')+b'A'*n

class UpdatingOrigin(Origin):
    def __init__(self,source,change):
        super().__init__(deadline_seconds=120)
        self.source,self.change,self.changed=source,change,False
        self.first_part_seen=False
    def _handler(self):
        base=super()._handler();owner=self
        class Handler(base):
            def _dispatch(self,path,query,body):
                answer=super()._dispatch(path,query,body)
                if answer[3]=='multipart-part' and query.get('partNumber')==['1']:
                    assert not owner.first_part_seen,'unexpected first-part retry'
                    assert len(body)==CHUNK,'multipart size changed; fixture needs review'
                    owner.first_part_seen=True
                    if owner.change:
                        with owner.source.open('r+b') as f:
                            f.seek(OFFSET);assert f.read(4096)==b'A'*4096
                            f.seek(OFFSET);f.write(b'B'*4096);f.flush();os.fsync(f.fileno())
                        assert owner.source.stat().st_size==TOTAL
                        owner.changed=True
                return answer
        return Handler

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--helper',type=Path,required=True);ap.add_argument('--helper-sha256',required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    assert hashlib.sha256(a.helper.read_bytes()).hexdigest()==a.helper_sha256,'wrong retained helper'
    assert shutil.disk_usage('/tmp').free>int(1.25*1024**3)+128*1024**2,'storage reserve'
    a.out.mkdir(parents=True,exist_ok=False)
    result={'complete':False,'scope':__doc__,'helper_sha256':a.helper_sha256,'cases':{}}
    started=time.monotonic()
    try:
        for change in (False,True):
            assert time.monotonic()-started<240
            name='changed' if change else 'unchanged';out=a.out/name;out.mkdir()
            with tempfile.TemporaryDirectory(prefix='s2-upload-') as td:
                root=Path(td);source=root/'model.safetensors';original=payload();source.write_bytes(original)
                modified=original[:OFFSET]+b'B'*4096+original[OFFSET+4096:]
                f=Fixture(a.helper.resolve(),root,out)
                c={'changed':change,'finished':False,'clean_shutdown':False,'original_sha384':sha(original),'changed_sha384':sha(modified)}
                try:
                    with UpdatingOrigin(source,change) as origin:
                        with f.running():
                            creds=root/'credentials';creds.write_text('aws_access_key_id=TEST_KEY_NOT_REAL\naws_secret_access_key=TEST_SECRET_NOT_REAL\n');creds.chmod(0o600)
                            cfg={'endpoint':origin.endpoint,'bucket':'fixture','prefix':name,'region':'us-east-1','provider':'GENERIC_S3','layout':'SOURCE_FILES','credential_ref':str(creds),'credential_ref_kind':'path','use_fake':False,'allow_http_loopback':True,'automatic_spend_atoms':0,'idempotency_key':name}
                            attached=f.ok('setcloudstorage',cfg);assert attached['applied'] and attached['automatic_spend_atoms']==0
                            reply=f.ok('importmodel',str(source),{'pin':True,'publish':False})
                            assert reply['automatic_spend_atoms']==0 and reply.get('artifact_id')
                            models=json.loads((f.model/'catalog.json').read_text())['models']
                            model=next(x for x in models if x['artifact_id']==reply['artifact_id'])
                            assert len(model['files'])==1
                            c['catalog_sha384']=model['files'][0]['sha384']
                            c['cloud_success']=reply.get('cloud_uploaded') is True
                            c['cloud_reply']=reply
                            c['first_part_seen']=origin.first_part_seen
                            assert c['first_part_seen'],'native upload never reached multipart boundary'
                            c['mutation_before_first_part_reply']=origin.changed
                            key=reply['cloud_files'][0]['object_key'];remote=origin.object_bytes('fixture/'+key)
                            c['remote_sha384']=sha(remote) if remote is not None else None
                            if remote is not None:assert len(remote)==TOTAL
                            assert sha(source.read_bytes())==(sha(modified) if change else sha(original))
                            c['origin']=origin.snapshot()
                        c['clean_shutdown']=True
                    c['finished']=True;c['observation']=classify(c)
                finally:
                    f.finish();(out/'result.json').write_text(json.dumps(c,indent=2)+'\n');result['cases'][name]=c
        result['complete']=True
    finally:
        result['seconds']=time.monotonic()-started;(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v['observation'] for k,v in result['cases'].items()}))
if __name__=='__main__':main()
