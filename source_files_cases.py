"""Two native cases only. Import has no execution side effects."""
import hashlib, json, math, os, signal, struct, time, subprocess, shutil
from pathlib import Path
from base_minio import ModelNetMinioLayoutsTest, ACCESS_SENTINEL, SECRET_SENTINEL
from test_framework.authproxy import JSONRPCException
from validate_source_files import validate

sha = lambda b: hashlib.sha384(b).hexdigest()
class SourceFilesCases(ModelNetMinioLayoutsTest):
    def set_test_params(self):
        super().set_test_params()
        self.started=time.monotonic()
        self.receipt={'schema':1,'backend':'real-MinIO','layout':'SOURCE_FILES','cases':{},'cleanup':False}
    def setup_nodes(self):
        root=Path(self.options.tmpdir).resolve()
        assert str(root).startswith('/tmp/btx-sf-'), 'owned short Ubuntu scratch required'
        super().setup_nodes()
    def _stop_helper(self):
        child=self.modeld_proc
        super()._stop_helper()
        if child is not None:
            assert child.poll()==0, 'helper did not exit cleanly'
            if hasattr(self,'receipt'):self.receipt.setdefault('helper_exits',[]).append(child.returncode)
    def _save(self):
        Path(self.options.tmpdir,'source-files-results.json').write_text(json.dumps(self.receipt,indent=2)+'\n')
    def call(self, method, *args):
        root=Path(self.options.tmpdir)
        if time.monotonic()-self.started>900:raise TimeoutError('whole native deadline')
        if sum(f.stat().st_size for f in root.rglob('*') if f.is_file())>256*1024**2:raise RuntimeError('fixture cap exceeded')
        if shutil.disk_usage(root).free<1.25*1024**3:raise RuntimeError('disk reserve')
        def expired(*_): raise TimeoutError('30s RPC deadline: '+method)
        prior=signal.signal(signal.SIGALRM,expired);signal.alarm(30)
        try:
            value=getattr(self.nodes[0],method)(*args)
            self.receipt.setdefault('rpc',[]).append({'method':method,'response':value})
            self._save();return self._zero_spend(value,method)
        finally:signal.alarm(0);signal.signal(signal.SIGALRM,prior)
    def counters(self):
        info=self.call('getcloudstorageinfo',{})
        def find(o):
            if isinstance(o,dict):
                if 'budget_used_gets_day' in o:return {k:o[k] for k in ('budget_used_gets_day','budget_day_utc')}
                for v in o.values():
                    z=find(v)
                    if z:return z
            return None
        result=find(info)
        if result is None:raise AssertionError('missing real S3 budget counters')
        return result
    def configure(self, key, cap=None):
        cfg=self._cloud_cfg('SOURCE_FILES',False);cfg['idempotency_key']=key
        if cap is not None:cfg['budget_gets_per_day']=cap
        applied=self.call('setcloudstorage',cfg)
        if applied.get('applied') is not True:raise AssertionError('cloud config not applied')
        self.cfg=dict(cfg)
    def preserve_and_remove_payload(self, stage):
        self._stop_helper();catalog=Path(self.modeldir,'catalog.json');before=sha(catalog.read_bytes())
        held=Path(self.options.tmpdir,'preserved',stage);held.mkdir(parents=True)
        checkout=Path(self.export['path'])
        if checkout.exists():checkout.rename(held/'checkout')
        if self.source.exists():self.source.rename(held/'original')
        tree=Path(self.modeldir,'store/artifacts',self.entry['artifact_id'])
        pieces=list(tree.rglob('*.piece'));assert pieces,'missing precondition pieces'
        for f in pieces:
            dest=held/'pieces'/f.relative_to(tree);dest.parent.mkdir(parents=True,exist_ok=True);f.rename(dest)
        assert sha(catalog.read_bytes())==before
        self._start_helper();self._wait_helper_ready()
        return before
    def inspect(self):
        result=self.call('exportmodelpath',self.entry['uri']);root=Path(result['path'])
        assert result['model_id']==self.entry['model_id'] and result['artifact_id']==self.entry['artifact_id']
        assert {f['path'] for f in result['files']}==set(self.expected)
        for rel,expected in self.expected.items():assert sha((root/rel).read_bytes())==expected
        self.export=result;return {'ids':{'model_id':result['model_id'],'artifact_id':result['artifact_id']},'files':dict(self.expected)}
    def run_test(self):
        self.creds=Path(self.options.tmpdir,'cloud-creds.ini');self.creds.write_text(f'access_key_id={ACCESS_SENTINEL}\nsecret_access_key={SECRET_SENTINEL}\n');os.chmod(self.creds,0o600)
        success=False
        try:
            self.endpoint=self._start_container();assert self.endpoint,'real MinIO unavailable; no fallback'
            assert self._s3('PUT')[0] in (200,409)
            self.configure('source-files-initial')
            self.source=Path(self.options.tmpdir,'source-files-input');self.source.mkdir();(self.source/'assets').mkdir()
            count=(8<<20)+(1<<16);header=json.dumps({'w':{'dtype':'U8','shape':[count],'data_offsets':[0,count]}},separators=(',',':')).encode()
            weights=struct.pack('<Q',len(header))+header+bytes(range(256))*(count//256)
            (self.source/'model.safetensors').write_bytes(weights);(self.source/'assets/config.json').write_text('{}\n')
            self.expected={str(f.relative_to(self.source)):sha(f.read_bytes()) for f in self.source.rglob('*') if f.is_file()}
            self.entry=self.call('importmodel',str(self.source),{'publish':False,'pin':True});assert self.entry['cloud_uploaded'] is True
            self.receipt['expected']={'ids':{'model_id':self.entry['model_id'],'artifact_id':self.entry['artifact_id']},'files':dict(self.expected)}
            self.export=self.call('exportmodelpath',self.entry['uri']);assert len(self.export['files'])==2
            large_index=next(i for i,f in enumerate(self.export['files']) if f['path']=='model.safetensors')
            before_catalog=self.preserve_and_remove_payload('B1');before=self.counters()
            got=self.call('getmodel',self.entry['uri']);assert got.get('cloud_hydrated') is True and not got.get('cloud_hydrate_error')
            first=self.inspect();after=self.counters();assert after['budget_used_gets_day']>before['budget_used_gets_day']
            self._restart_helper();self.call('getmodel',self.entry['uri']);again=self.inspect();assert first==again and self.counters()==after
            self.receipt['cases']['B1']={'status':'PASS','catalog_hash_unchanged':before_catalog,'before':before,'after':after,'restored':first,'restart':again,'direct_seed_flags_used':False};self._save()
            # A distinct already-local model must remain usable while cloud reads are capped.
            healthy=Path(self.options.tmpdir,'healthy');healthy.mkdir();(healthy/'model.safetensors').write_bytes(struct.pack('<Q',2)+b'{}')
            healthy_entry=self.call('importmodel',str(healthy),{'publish':False,'pin':True})
            baseline=self.counters();cap=baseline['budget_used_gets_day']+70;self.configure('source-files-limit',cap)
            self.preserve_and_remove_payload('B2');failed=self.call('getmodel',self.entry['uri'])
            assert 'budget exhausted' in str(failed.get('cloud_hydrate_error','')).lower() and failed.get('status')!='local'
            cursor_path=Path(self.modeldir,'file_stream_jobs',f"{self.entry['artifact_id']}-{large_index}.json");cursor=json.loads(cursor_path.read_text());assert cursor['resume_offset']>=4<<20 and cursor['next_piece']>=1
            prefix=Path(self.modeldir,'cloud-hydrate-q/artifacts',self.entry['artifact_id'],str(large_index),'0.piece');assert sha(prefix.read_bytes())==sha(weights[:4<<20])
            try:self.call('exportmodelpath',self.entry['uri'])
            except JSONRPCException as exc:assert 'INCOMPLETE' in str(exc)
            else:raise AssertionError('partial model exported')
            charged=self.counters();assert charged['budget_used_gets_day']==cap
            healthy_export=self.call('exportmodelpath',healthy_entry['uri']);assert Path(healthy_export['path'],'model.safetensors').read_bytes()==struct.pack('<Q',2)+b'{}'
            self._restart_helper();assert self.counters()==charged
            retry=self.call('getmodel',self.entry['uri']);assert 'budget exhausted' in str(retry.get('cloud_hydrate_error','')).lower();assert self.counters()==charged
            assert json.loads(cursor_path.read_text())['resume_offset']==cursor['resume_offset'] and sha(prefix.read_bytes())==sha(weights[:4<<20])
            self.configure('source-files-relief',cap+1000);assert self.counters()==charged
            recovered=self.call('getmodel',self.entry['uri']);assert recovered.get('cloud_hydrated') is True and not recovered.get('cloud_hydrate_error')
            final=self.inspect();end=self.counters();delta=end['budget_used_gets_day']-charged['budget_used_gets_day'];assert 0<delta<math.ceil(len(weights)/65536)
            assert end['budget_day_utc']==baseline['budget_day_utc'],'UTC rollover invalidates budget comparison'
            self._restart_helper();last=self.inspect();assert final==last and self.counters()==end
            self.receipt['cases']['B2']={'status':'PASS','charged':charged,'cap':cap,'baseline':baseline,'after':end,'resume_offset':cursor['resume_offset'],'resume_gets':delta,'full_large_reads':math.ceil(len(weights)/65536),'restored':final,'restart':last,'healthy_control':True,'persistent_refusal':True,'direct_seed_flags_used':False};success=True
        except Exception as exc:
            self.receipt['failure']=repr(exc);raise
        finally:
            self._stop_helper();container=self.container;self._stop_container()
            if container:
                check=subprocess.run([str(self.docker),'inspect',container],capture_output=True,timeout=30)
                assert check.returncode!=0, 'owned MinIO container still exists'
            assert self.modeld_proc is None and self.container is None
            self.receipt['cleanup']=True;self.receipt['native_body_completed']=success;self._save()
        validate(self.receipt)
if __name__=='__main__':SourceFilesCases(__file__).main()
