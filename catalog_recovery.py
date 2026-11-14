"""Disposable catalog deletion; surviving-checkout recovery and cloud-only control."""
import hashlib,json,shutil,struct
from pathlib import Path
from feature_modelnet_minio import ModelNetMinioLayoutsTest

class CatalogRecovery(ModelNetMinioLayoutsTest):
    def _start_container(self):
        ep=super()._start_container()
        assert ep,self.not_run
        return ep
    def _run_partial_cloud_recovery(self):
        pass
    def _run_matrix(self,fake):
        assert not fake,'No FakeS3 fallback'
        node=self.nodes[0]
        result={'phase':'SETUP','platform':'Ubuntu24.04-x86_64','catalog_fault':'file removed while helper stopped; no JSON flag edits','helper_profile':'retained PR707 candidate; unchanged catalog recovery paths; older RPC proxy'}
        output=Path(self.options.tmpdir)/'catalog-recovery-result.json'
        def save():output.write_text(json.dumps(result,indent=2))
        def same_remote(artifact,original):
            return self._reconstruct_object(self._bucket_keys(),artifact)==original
        def absent_export(uri):
            try:node.exportmodelpath(uri)
            except Exception as e:
                assert 'NOT_FOUND' in str(e),str(e)
                return str(e)
            raise AssertionError('missing catalog unexpectedly exported')
        def verify_local(uri,original,model,artifact):
            got=self._zero_spend(node.getmodel(uri),'getmodel local')
            assert got.get('status')=='local',got
            assert got['model_id']==model and got['artifact_id']==artifact,got
            exported=node.exportmodelpath(uri)
            p=Path(exported['path'])/'model.safetensors'
            assert p.read_bytes()==original,exported
            return got,exported
        try:
            self._zero_spend(node.setcloudstorage(self._cloud_cfg('PIECE_OBJECTS',False)),'configure real MinIO')
            count=4096;payload=bytes(range(256))*16
            header=json.dumps({'w':{'dtype':'U8','shape':[count],'data_offsets':[0,count]}},separators=(',',':')).encode()
            original=struct.pack('<Q',len(header))+header+payload
            source=Path(self.options.tmpdir)/'original'/'model.safetensors'
            source.parent.mkdir();source.write_bytes(original)
            entry=self._zero_spend(node.importmodel(str(source)),'initial import')
            assert entry.get('cloud_uploaded') is True,entry
            uri,artifact,model=entry['uri'],entry['artifact_id'],entry['model_id']
            result.update(model_id=model,artifact_id=artifact,sha384=hashlib.sha384(original).hexdigest(),size=len(original),uri=uri)
            _,export=verify_local(uri,original,model,artifact)
            checkout=Path(export['path']);assert (checkout/'model.safetensors').read_bytes()==original
            cat=Path(self.modeldir)/'catalog.json';root=Path(self.modeldir)/'store/artifacts'/artifact
            piece_snapshot={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*.piece')}
            assert piece_snapshot and same_remote(artifact,original)
            result['healthy_control']=True;save()

            # Only the catalog file is faulted. Original bytes, checkout, pieces,
            # cloud configuration, search records and remote objects survive.
            self._stop_helper();saved_catalog=cat.read_bytes();cat.unlink()
            self._start_helper();self._wait_helper_ready()
            missing=self._zero_spend(node.getmodel(uri),'missing catalog observation')
            result['catalog_missing_response']=missing
            result['catalog_missing_export_error']=absent_export(uri)
            assert missing.get('status')=='not_local' and missing.get('peers')==0,missing
            result['catalog_missing_not_local']=True
            current_pieces={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*.piece')}
            assert current_pieces==piece_snapshot
            result['committed_pieces_survived']=True
            assert same_remote(artifact,original)
            result['catalog_missing_remote_bytes_survived']=True
            # Prove the recovery input is the exported checkout, not the original.
            source.unlink()
            reimport=self._zero_spend(node.importmodel(str(checkout),{'publish':False,'pin':True}),'reimport surviving checkout')
            result['checkout_reimport']=reimport
            assert reimport['model_id']==model and reimport['artifact_id']==artifact,reimport
            result['checkout_reimport_identity_match']=True
            verify_local(uri,original,model,artifact);result['checkout_reimport_bytes_match']=True
            self._restart_helper();verify_local(uri,original,model,artifact)
            result['checkout_reimport_restart_pass']=True;save()

            # Different, explicit total-local-loss case; the origin is unchanged.
            self._stop_helper();cat.unlink();shutil.rmtree(checkout);shutil.rmtree(root)
            assert not source.exists() and not checkout.exists() and not root.exists()
            self._start_helper();self._wait_helper_ready()
            cloud_only=self._zero_spend(node.getmodel(uri),'cloud-only observation')
            result['cloud_only_response']=cloud_only
            result['cloud_only_export_error']=absent_export(uri)
            assert cloud_only.get('status')=='not_local' and cloud_only.get('peers')==0,cloud_only
            result['cloud_only_not_local']=True
            assert same_remote(artifact,original);result['cloud_only_remote_bytes_survived']=True
            # A normal supported reimport remains possible; no catalog restore/edit.
            source.write_bytes(original)
            restored=self._zero_spend(node.importmodel(str(source),{'publish':False,'pin':True}),'normal reimport control')
            assert restored['model_id']==model and restored['artifact_id']==artifact,restored
            verify_local(uri,original,model,artifact);self._restart_helper();verify_local(uri,original,model,artifact)
            result['normal_reimport_restart_pass']=True
            result['phase']='QUALIFIED_METADATA_BOUNDARY'
            self._assert_no_sentinel_in_logs('catalog recovery complete')
            save()
        finally:save()
if __name__=='__main__':CatalogRecovery(__file__).main()
