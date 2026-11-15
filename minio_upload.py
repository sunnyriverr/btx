#!/usr/bin/env python3
"""Narrow real-MinIO SOURCE_FILES control; no FakeS3 fallback or state edits.
Staged alongside the previously verified base_minio.py and test_framework.
"""
import hashlib,json,os,re,struct,urllib.request,subprocess
from pathlib import Path
from base_minio import ModelNetMinioLayoutsTest,ACCESS_SENTINEL,SECRET_SENTINEL

CHUNK=8<<20

def write_exact_model(path,total=2*CHUNK):
    # Fixed-width JSON integers keep header length stable while fitting file exactly.
    header_size=128
    n=total-8-header_size
    header=json.dumps({'w':{'dtype':'U8','shape':[n],'data_offsets':[0,n]}},separators=(',',':')).encode()
    assert len(header)<=header_size
    blob=struct.pack('<Q',header_size)+header.ljust(header_size,b' ')+(bytes(range(256))*((n+255)//256))[:n]
    assert len(blob)==total
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(blob)
    return hashlib.sha384(blob).hexdigest()

class UploadControl(ModelNetMinioLayoutsTest):
    def set_test_params(self):
        super().set_test_params()

    def _minio_image(self):
        ref=os.environ.get('BTX_MINIO_IMAGE','')
        assert ref.startswith('sha256:') or '@sha256:' in ref, 'pin existing MinIO image by digest/ID'
        r=subprocess.run([str(self.docker),'image','inspect',ref],capture_output=True,text=True,timeout=15)
        assert r.returncode==0, 'BLOCKED: pinned image not present; no latest-image fallback'
        self.minio_image_id=json.loads(r.stdout)[0]['Id']
        return ref

    def _start_container(self):
        self.docker=self._docker_bin()
        assert self.docker is not None, 'BLOCKED: Docker unavailable'
        self._minio_image()  # Must succeed before inherited fixture can attempt a pull.
        return super()._start_container()

    def head(self,key,query=''):
        with urllib.request.urlopen(self._sigv4('HEAD',key,query),timeout=30) as r:
            assert r.status==200
            return {k.lower():v for k,v in r.headers.items()}

    def run_test(self):
        receipt=Path(self.options.tmpdir)/'bounded-upload.json'
        out={'status':'INCOMPLETE','provider':'MINIO','fake':False,'source_bytes':2*CHUNK}
        def save(): receipt.write_text(json.dumps(out,indent=2)+'\n')
        self.creds=Path(self.options.tmpdir)/'cloud-creds.ini'
        self.creds.write_text(f'access_key_id={ACCESS_SENTINEL}\nsecret_access_key={SECRET_SENTINEL}\n');os.chmod(self.creds,0o600)
        save()
        try:
            self.endpoint=self._start_container()
            assert self.endpoint is not None, 'BLOCKED: real MinIO unavailable; no fallback'
            out['minio_image_id']=self.minio_image_id;save()
            assert self._s3('PUT')[0] in (200,409)
            node=self.nodes[0]
            cfg=self._zero_spend(node.setcloudstorage(self._cloud_cfg('SOURCE_FILES',False)),'configure')
            info=self._zero_spend(node.getcloudstorageinfo({}),'info')
            assert info.get('layout')=='SOURCE_FILES', info
            path=Path(self.options.tmpdir)/'upload-control/model.safetensors'
            out['source_sha384']=write_exact_model(path)
            entry=self._zero_spend(node.importmodel(str(path)),'import')
            assert entry.get('cloud_uploaded') is True, entry
            uri=entry.get('uri') or entry.get('model_id');artifact=entry.get('artifact_id')
            assert uri and artifact
            keys=self._bucket_keys();files=[k for k in (keys or []) if artifact in k and re.search(r'/files/\d+$',k)]
            assert len(files)==1, files
            key=files[0];out['head']=self.head(key)
            assert out['head'].get('etag','').strip('"').endswith('-2'), out['head']
            out['part_heads']=[self.head(key,f'partNumber={n}') for n in (1,2)]
            assert [int(h['content-length']) for h in out['part_heads']]==[CHUNK,CHUNK],out['part_heads']
            assert int(out['head']['content-length'])==2*CHUNK
            def verify(label):
                status,body=self._s3('GET',key=key)
                assert status==200 and len(body)==2*CHUNK
                assert hashlib.sha384(body).hexdigest()==out['source_sha384']
                got=self._zero_spend(node.getmodel(uri),label)
                assert got.get('uri')==uri and got.get('artifact_id')==artifact,got
                out[label]=True;save()
            verify('before_restart');self._restart_helper()
            assert node.getcloudstorageinfo({}).get('layout')=='SOURCE_FILES'
            verify('after_restart');self._assert_no_sentinel_in_logs('bounded upload')
            out['status']='PASS';save()
        except Exception as e:
            out['status']='FAIL_OR_BLOCKED';out['error']=str(e);save();raise
        finally:
            self._stop_container()

if __name__=='__main__': UploadControl(__file__).main()
