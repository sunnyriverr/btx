import hashlib,json,struct,shutil,os
from pathlib import Path
from feature_modelnet_minio import ModelNetMinioLayoutsTest
class Case(ModelNetMinioLayoutsTest):
    def set_test_params(self):super().set_test_params()
    def run_test(self):super().run_test()
    def _run_partial_cloud_recovery(self):pass
    def _run_corrected_origin_recovery(self):pass
    def _start_container(self):
        ep=super()._start_container();assert ep,self.not_run;return ep
    def _run_matrix(self,fake):
        assert not fake
        node=self.nodes[0];all_results=[]
        for variant in ['missing-quarantine','missing-job','marker-write-failure']:
            result={};output=Path(self.options.tmpdir)/(variant+'.json')
            def save():output.write_text(json.dumps(result,indent=2))
            def sha(b):return hashlib.sha384(b).hexdigest()
            self._zero_spend(node.setcloudstorage(self._cloud_cfg('PIECE_OBJECTS',False)),'configure')
            count=2*(4<<20)+4096;payload=(bytes(range(256))*((count+255)//256))[:count];payload=bytes([{'missing-quarantine':1,'missing-job':2,'marker-write-failure':3}[variant]])+payload[1:]
            header=json.dumps({'w':{'dtype':'U8','shape':[count],'data_offsets':[0,count]}},separators=(',',':')).encode()
            original=struct.pack('<Q',len(header))+header+payload
            source=Path(self.options.tmpdir)/variant/'model.safetensors';source.parent.mkdir();source.write_bytes(original)
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
            assert self._s3('PUT',key=key,body=remote_piece)[0] in [200,204]
            assert self._reconstruct_object(self._bucket_keys(),artifact)==original
            self._stop_helper()
            marker=cursor_path.with_name(cursor_path.name+'.rejected')
            untouched=quarantine.parent/'9'/'sentinel.piece';untouched.parent.mkdir();untouched.write_bytes(b'unrelated quarantine path')
            if variant=='marker-write-failure':
                assert os.getuid()!=0,'Permission fault requires an unprivileged helper'
                # Explicit fixture injection of the already-observed rejected EOF state.
                (quarantine/'1.piece').write_bytes(bytes([remote_piece[0]^1])+remote_piece[1:])
                (quarantine/'2.piece').write_bytes(original[2*piece_bytes:])
                cursor['next_piece']=3;cursor['resume_offset']=3*piece_bytes
                cursor_path.write_text(json.dumps(cursor))
                saved_job=cursor_path.read_bytes();saved_q={p.name:sha(p.read_bytes()) for p in quarantine.glob('*.piece')}
                jobs=cursor_path.parent;jobs.chmod(0o555)
                self._start_helper();self._wait_helper_ready()
                try:
                    denied=node.getmodel(uri)
                    assert 'invalidation failed' in denied.get('cloud_hydrate_error',''),denied
                    assert cursor_path.read_bytes()==saved_job
                    assert {p.name:sha(p.read_bytes()) for p in quarantine.glob('*.piece')}==saved_q
                    assert not list(root.rglob('*.piece'))
                finally:jobs.chmod(0o755)
                rejected=node.getmodel(uri);assert 'mismatch' in rejected.get('cloud_hydrate_error',''),rejected
            else:
                marker.write_text('file integrity rejected\n')
                if variant=='missing-quarantine':shutil.rmtree(quarantine)
                else:cursor_path.unlink()
                self._start_helper();self._wait_helper_ready()
            got=self._zero_spend(node.getmodel(uri),'resume marked cleanup')
            assert got.get('status')=='local',got
            pieces=sorted(root.rglob('*.piece'),key=lambda p:int(p.stem));assert b''.join(p.read_bytes() for p in pieces)==original
            exported=self._zero_spend(node.exportmodelpath(uri),'export cleanup result');assert (Path(exported['path'])/source.name).read_bytes()==original
            assert not marker.exists() and not cursor_path.exists()
            assert untouched.read_bytes()==b'unrelated quarantine path'
            self._restart_helper();assert node.getmodel(uri).get('status')=='local'
            all_results.append({'variant':variant,'recovered_exactly':True,'restart_local':True,'unrelated_path_preserved':True,'fixture':'Explicit local filesystem state injection, not a timed process crash'})
        Path(self.options.tmpdir,'cleanup-controls.json').write_text(json.dumps(all_results,indent=2))
if __name__=='__main__':Case(__file__).main()
