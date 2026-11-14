"""Real PIECE_OBJECTS origin failure after one checkpoint; no local state edits."""
import hashlib,json,struct,time
from pathlib import Path
from feature_modelnet_minio import ModelNetMinioLayoutsTest

class CorruptResume(ModelNetMinioLayoutsTest):
    def set_test_params(self):super().set_test_params()
    def run_test(self):super().run_test()
    def _start_container(self):
        ep=super()._start_container();assert ep,self.not_run;return ep
    def _run_matrix(self,fake):
        assert not fake
        node=self.nodes[0];result={'phase':'SETUP','fixture_state_edits':False}
        output=Path(self.options.tmpdir)/'partial-retry-result.json'
        def save():output.write_text(json.dumps(result,indent=2))
        def sha(b):return hashlib.sha384(b).hexdigest()
        try:
            self._zero_spend(node.setcloudstorage(self._cloud_cfg('PIECE_OBJECTS',False)),'configure')
            count=2*(4<<20)+4096;payload=(bytes(range(256))*((count+255)//256))[:count]
            header=json.dumps({'w':{'dtype':'U8','shape':[count],'data_offsets':[0,count]}},separators=(',',':')).encode()
            original=struct.pack('<Q',len(header))+header+payload
            source=Path(self.options.tmpdir)/'multi-piece'/'model.safetensors';source.parent.mkdir();source.write_bytes(original)
            entry=self._zero_spend(node.importmodel(str(source)),'import');assert entry['cloud_uploaded']
            uri,artifact=entry['uri'],entry['artifact_id'];root=Path(self.modeldir)/'store/artifacts'/artifact
            assert self._reconstruct_object(self._bucket_keys(),artifact)==original
            paths=sorted(root.rglob('*.piece'),key=lambda p:int(p.stem));assert len(paths)==3 and len(paths[0].read_bytes())==4<<20
            first=paths[0].read_bytes();piece_bytes=4<<20
            self._zero_spend(node.getmodel(uri),'healthy getmodel')
            result.update(phase='HEALTHY',size=len(original),sha384=sha(original),artifact=artifact,model_id=entry['model_id']);save()
            keys=[k for k in self._bucket_keys() if artifact in k and k.endswith('/0/1.piece')];assert len(keys)==1
            key=keys[0];status,remote_piece=self._s3('GET',key=key);assert status==200
            assert self._s3('DELETE',key=key)[0] in [200,204]
            self._stop_helper();cat=Path(self.modeldir)/'catalog.json';saved_catalog=cat.read_bytes()
            for p in paths:p.unlink()
            source.unlink();assert cat.read_bytes()==saved_catalog
            self._start_helper();self._wait_helper_ready()
            failed=self._zero_spend(node.getmodel(uri),'partial origin failure')
            cursor_path=Path(self.modeldir)/'file_stream_jobs'/f'{artifact}-0.json'
            cursor=json.loads(cursor_path.read_text());quarantine=Path(self.modeldir)/'cloud-hydrate-q/artifacts'/artifact/'0'
            result.update(phase='PARTIAL_FAILURE',first_response=failed,partial_cursor=cursor,quarantine_piece0_sha384=sha((quarantine/'0.piece').read_bytes()))
            save()
            assert cursor['next_piece']==1 and cursor['resume_offset']==piece_bytes,cursor
            assert cursor['have_sha'] and cursor['have_root']
            assert (quarantine/'0.piece').read_bytes()==first
            assert failed.get('status')!='local' and failed.get('cloud_hydrate_error'),failed
            assert not list(root.rglob('*.piece'))
            try:node.exportmodelpath(uri)
            except Exception as e:result['partial_export_error']=str(e)
            else:raise AssertionError('partial model was usable')
            bad_piece=bytes([remote_piece[0]^1])+remote_piece[1:]
            assert self._s3('PUT',key=key,body=bad_piece)[0] in [200,204]
            assert self._reconstruct_object(self._bucket_keys(),artifact)!=original
            result['origin_restored_byte_identical']=False
            def retry():
                observations=[];deadline=time.monotonic()+20
                while True:
                    got=self._zero_spend(node.getmodel(uri),'ordinary same-model retry');observations.append(got)
                    error=str(got.get('cloud_hydrate_error','')).lower()
                    if not any(k in error for k in ['backoff','cooldown','rate limit']) or time.monotonic()>=deadline:return observations
                    time.sleep(.5)
            result['retry_responses']=retry()
            result['retry_cursor']=json.loads(cursor_path.read_text()) if cursor_path.exists() else None
            result['retry_quarantine']={p.name:sha(p.read_bytes()) for p in quarantine.glob('*.piece')}
            def inspect(label):
                pieces=sorted(root.rglob('*.piece'),key=lambda p:int(p.stem));result[label+'_bytes_match']=b''.join(p.read_bytes() for p in pieces)==original
                try:
                    exported=self._zero_spend(node.exportmodelpath(uri),'materialize retry')
                    result[label+'_materialized_match']=(Path(exported['path'])/source.name).read_bytes()==original
                except Exception as e:result[label+'_export_error']=str(e)
            inspect('retry');save()
            self._restart_helper();result['after_restart_responses']=retry();inspect('restart')
            result['restart_cursor']=json.loads(cursor_path.read_text()) if cursor_path.exists() else None
            for label,responses in [('retry',result['retry_responses']),('restart',result['after_restart_responses'])]:
                error=responses[-1].get('cloud_hydrate_error','').lower()
                assert 'mismatch' in error and ('sha' in error or 'root' in error),responses
                assert result[label+'_bytes_match'] is False,result
                assert 'INCOMPLETE' in result[label+'_export_error'],result
                assert not list(root.rglob('*.piece')),'bad resumed model reached live store'
            result['phase']='RESUMED_CORRUPTION_REFUSED'
            save();print('RESUMED_CORRUPTION_REFUSED',flush=True)
        finally:save()

if __name__=='__main__':CorruptResume(__file__).main()
