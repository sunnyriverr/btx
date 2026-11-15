import hashlib,json,struct,shutil
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
        node=self.nodes[0];result={}
        def save():Path(self.options.tmpdir,'quota-eof-result.json').write_text(json.dumps(result,indent=2))
        def sha(b):return hashlib.sha384(b).hexdigest()
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
        self._stop_helper();catalog=Path(self.modeldir)/'catalog.json';before=catalog.read_bytes()
        for p in paths:p.unlink()
        source.unlink();assert catalog.read_bytes()==before
        self._start_helper();self._wait_helper_ready()
        filler=Path(self.options.tmpdir)/'filler.safetensors';n=60*(1<<20)
        h=json.dumps({'w':{'dtype':'U8','shape':[n],'data_offsets':[0,n]}},separators=(',',':')).encode()
        filler.write_bytes(struct.pack('<Q',len(h))+h+bytes([0x55])*n)
        entry2=self._zero_spend(node.importmodel(str(filler)),'pinned filler import')
        got=node.getmodel(uri);assert got.get('cloud_hydrate_error')=='disk quota',got
        job=Path(self.modeldir)/'file_stream_jobs'/f'{artifact}-0.json';q=Path(self.modeldir)/'cloud-hydrate-q/artifacts'/artifact/'0'
        record=json.loads(job.read_text());assert record['next_piece']==3,record
        expected={p.name:sha(p.read_bytes()) for p in q.glob('*.piece')};assert len(expected)==3
        self._zero_spend(node.removemodel(entry2['uri']),'remove disposable filler')
        assert {p.name:sha(p.read_bytes()) for p in q.glob('*.piece')}==expected
        got=self._zero_spend(node.getmodel(uri),'resume valid EOF');assert got.get('status')=='local' and got.get('origin_get_ops')==0,got
        exported=self._zero_spend(node.exportmodelpath(uri),'export EOF');assert (Path(exported['path'])/source.name).read_bytes()==original
        assert not job.exists()
        self._restart_helper();assert node.getmodel(uri).get('status')=='local'
        result.update(phase='VALID_EOF_QUOTA_RESUME_PASS',origin_get_ops=0,exact_export=True,restart_local=True);save()
if __name__=='__main__':Case(__file__).main()
