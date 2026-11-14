"""Native negative controls, using the retained real-MinIO fixture (no flags)."""
import hashlib,json
from pathlib import Path
from feature_modelnet_minio import ModelNetMinioLayoutsTest,write_safetensors

class CloudRecoveryControls(ModelNetMinioLayoutsTest):
    def set_test_params(self): super().set_test_params()
    def run_test(self): super().run_test()
    def _start_container(self):
        ep=super()._start_container(); assert ep,self.not_run; return ep
    def _run_matrix(self,fake):
        assert not fake
        node=self.nodes[0];cases=[]
        self._zero_spend(node.setcloudstorage(self._cloud_cfg('PIECE_OBJECTS',False)),'healthy configure')
        healthy_src=Path(self.options.tmpdir)/'healthy-control'/'model.safetensors'
        healthy_sha=write_safetensors(healthy_src,'healthy control\n')
        healthy=self._zero_spend(node.importmodel(str(healthy_src)),'healthy import')
        healthy_uri=healthy['uri']
        for case in ['corrupt-origin','budget-refusal']:
            cfg=self._cloud_cfg('PIECE_OBJECTS',False);cfg['idempotency_key']='cloud-control-'+case+'-initial'
            self._zero_spend(node.setcloudstorage(cfg),'configure')
            src=Path(self.options.tmpdir)/case/'model.safetensors';digest=write_safetensors(src,case+'\n');original=src.read_bytes()
            entry=self._zero_spend(node.importmodel(str(src)),'import');assert entry['cloud_uploaded']
            uri,artifact=entry['uri'],entry['artifact_id'];assert self._reconstruct_object(self._bucket_keys(),artifact)==original
            if case=='corrupt-origin':
                keys=[k for k in self._bucket_keys() if artifact in k and k.endswith('/0/0.piece')];assert len(keys)==1
                bad=bytes([original[0]^1])+original[1:];assert self._s3('PUT',key=keys[0],body=bad)[0] in [200,204]
            else:
                cfg['budget_gets']=0;cfg['idempotency_key']='cloud-control-budget-refusal-zero'
                self._zero_spend(node.setcloudstorage(cfg),'zero GET budget')
            self._stop_helper();cat=Path(self.modeldir)/'catalog.json';saved=cat.read_bytes();root=Path(self.modeldir)/'store/artifacts'/artifact
            pieces=list(root.rglob('*.piece'));assert pieces
            for p in pieces:p.unlink()
            src.unlink();assert cat.read_bytes()==saved
            self._start_helper();self._wait_helper_ready()
            response=self._zero_spend(node.getmodel(uri),'refused hydrate')
            Path(self.options.tmpdir,'cloud-controls-partial.json').write_text(json.dumps({'case':case,'response':response},indent=2))
            assert response.get('status')!='local',response
            error=response.get('cloud_hydrate_error','');assert error,error
            if case=='corrupt-origin':assert 'mismatch' in error.lower() and ('sha' in error.lower() or 'root' in error.lower()),error
            else:assert 'budget' in error.lower(),error
            assert not list(root.rglob('*.piece')),'unverified origin bytes reached live store'
            try:node.exportmodelpath(uri)
            except Exception as e:export_error=str(e)
            else:raise AssertionError('export accepted unverified/missing bytes')
            healthy_get=self._zero_spend(node.getmodel(healthy_uri),'healthy model with refused origin')
            assert healthy_get.get('status')=='local' and not healthy_get.get('cloud_hydrated'),healthy_get
            checkout=self._zero_spend(node.exportmodelpath(healthy_uri),'healthy export')
            assert hashlib.sha384((Path(checkout['path'])/healthy_src.name).read_bytes()).hexdigest()==healthy_sha
            cases.append({'healthy_model_passed':True,'case':case,'response':response,'export_error':export_error,'live_pieces':0})
        Path(self.options.tmpdir,'cloud-controls.json').write_text(json.dumps(cases,indent=2))
        print('CLOUD_HASH_AND_BUDGET_CONTROLS_PASS',flush=True)

if __name__=='__main__':CloudRecoveryControls(__file__).main()
