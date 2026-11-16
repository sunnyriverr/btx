import hashlib,json,os,re,shutil
from pathlib import Path
from minio_upload import UploadControl,write_exact_model,ACCESS_SENTINEL,SECRET_SENTINEL
class RehostCases(UploadControl):
    def set_test_params(self): super().set_test_params()
    def run_test(self):
        receipt=Path(os.environ['BTX_UPLOAD_RECEIPT']);out={'status':'INCOMPLETE','provider':'MINIO','fake':False,'attempts':{}}
        def save():receipt.write_text(json.dumps(out,indent=2)+'\n')
        self.creds=Path(self.options.tmpdir)/'cloud-creds.ini';self.creds.write_text(f'access_key_id={ACCESS_SENTINEL}\nsecret_access_key={SECRET_SENTINEL}\n');os.chmod(self.creds,0o600)
        original=Path(self.options.tmpdir)/'original/model.safetensors';retained=Path(self.options.tmpdir)/'retained/model.safetensors';copy=Path(self.options.tmpdir)/'relocated/model.safetensors'
        save()
        try:
            self.endpoint=self._start_container();assert self.endpoint
            assert self._s3('PUT')[0] in (200,409)
            node=self.nodes[0];self._zero_spend(node.setcloudstorage(self._cloud_cfg('SOURCE_FILES',False)),'configure')
            out['source_sha384']=write_exact_model(original);copy.parent.mkdir();shutil.copy2(original,copy)
            first=self._zero_spend(node.importmodel(str(original)),'first');assert first.get('cloud_uploaded') is True
            uri=first['uri'];artifact=first['artifact_id'];out.update(uri=uri,artifact=artifact)
            keys=[k for k in self._bucket_keys() if artifact in k and re.search(r'/files/\d+$',k)];assert len(keys)==1;key=keys[0]
            def check_bytes(path):assert hashlib.sha384(path.read_bytes()).hexdigest()==out['source_sha384']
            def attempt(label,path):
                check_bytes(path);assert self._s3('DELETE',key=key)[0] in (200,204)
                assert self._s3('GET',key=key)[0]==404
                response=self._zero_spend(node.hostmodel(str(path)),label)
                assert response.get('uri')==uri and response.get('artifact_id')==artifact
                assert type(response.get('cloud_uploaded')) is bool
                status,body=self._s3('GET',key=key)
                if response['cloud_uploaded']:assert status==200 and hashlib.sha384(body).hexdigest()==out['source_sha384']
                else:assert status==404
                out['attempts'][label]={'response':response,'remote_status':status,'remote_bytes_match':status==200 and hashlib.sha384(body).hexdigest()==out['source_sha384']};save()
            attempt('same_path',original);assert out['attempts']['same_path']['response']['cloud_uploaded'] is True
            retained.parent.mkdir();original.rename(retained);check_bytes(retained);assert not original.exists()
            attempt('relocated_copy',copy)
            self._restart_helper();assert not original.exists();attempt('relocated_after_restart',copy)
            export=self._zero_spend(node.exportmodelpath(uri),'export');out['export']=export
            checkout=Path(export['path']);source=checkout/'model.safetensors' if checkout.is_dir() else checkout;check_bytes(source)
            attempt('materialized_checkout',checkout)
            retained.rename(original);attempt('original_path_restored',original)
            assert out['attempts']['original_path_restored']['response']['cloud_uploaded'] is True
            check_bytes(original);check_bytes(copy);out['originals_preserved']=True
            failed=[not out['attempts'][n]['response']['cloud_uploaded'] for n in ('relocated_copy','relocated_after_restart','materialized_checkout')]
            out['classification']='STALE_SOURCE_PATH_REPRODUCED' if all(failed) else 'REVIEW_OBSERVATIONS'
            out['status']='COMPLETE';save()
        except Exception as exc:out['status']='FAIL_OR_BLOCKED';out['error']=str(exc);save();raise
        finally:self._stop_container()
if __name__=='__main__':RehostCases(__file__).main()
