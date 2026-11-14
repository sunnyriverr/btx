"""Current helper only; use maintained cloud recovery bodies, not the full layout matrix."""
import hashlib,json,shutil
from pathlib import Path
from feature_modelnet_minio import ModelNetMinioLayoutsTest,write_safetensors
class IntegratedRecovery(ModelNetMinioLayoutsTest):
    def set_test_params(self):super().set_test_params()
    def run_test(self):super().run_test()
    def _start_container(self):
        ep=super()._start_container();assert ep,self.not_run;return ep
    def _run_partial_cloud_recovery(self):
        super()._run_partial_cloud_recovery()
        shutil.copyfile(Path(self.options.tmpdir)/"partial-retry-result.json",Path(self.options.tmpdir)/"partial-valid-result.json")
    def _run_corrected_origin_recovery(self):
        super()._run_corrected_origin_recovery()
        shutil.copyfile(Path(self.options.tmpdir)/"partial-retry-result.json",Path(self.options.tmpdir)/"corrected-origin-result.json")
    def _run_matrix(self,fake):
        assert not fake
        node=self.nodes[0]
        self._zero_spend(node.setcloudstorage(self._cloud_cfg('PIECE_OBJECTS',False)),'configure real MinIO')
        source=Path(self.options.tmpdir)/'normal-current'/'model.safetensors'
        digest=write_safetensors(source,'current integrated normal recovery\n')
        original=source.read_bytes();entry=self._zero_spend(node.importmodel(str(source)),'normal import')
        assert entry['cloud_uploaded'] is True
        assert self._reconstruct_object(self._bucket_keys(),entry['artifact_id'])==original
        source.unlink()
        self._assert_piece_objects_hydrate_incomplete('MinIO',False,entry['uri'],entry['artifact_id'],digest)
        exported=self._zero_spend(node.exportmodelpath(entry['uri']),'normal export')
        assert (Path(exported['path'])/source.name).read_bytes()==original
        Path(self.options.tmpdir,'normal-current-result.json').write_text(json.dumps({'phase':'NORMAL_RECOVERY_PASS','model_id':entry['model_id'],'artifact_id':entry['artifact_id'],'sha384':hashlib.sha384(original).hexdigest(),'exact_export':True,'restart_local':True,'fixture_catalog_flags_edited':False},indent=2))
if __name__=='__main__':IntegratedRecovery(__file__).main()
