"""Same acceptance assertions for retained baseline and patched daemon.
Native local lab RPC; permit consumption does not claim model dispatch.
"""
import os,json,time,subprocess,urllib.request,urllib.error,base64,hashlib,shutil
from pathlib import Path
import pytest
D=Path(__file__).resolve().parent
class RPCError(Exception):pass
@pytest.fixture
def lab(tmp_path,request):
    root=tmp_path;node=root/'node';node.mkdir();state=root/'lab';state.mkdir();events=[];counter=0
    binary=Path(os.environ['BTX_ROLLBACK_BINARY']).resolve();log=(root/'node.log').open('w')
    argv=[str(binary),'-regtest','-datadir='+str(node),'-rpcport=39361','-port=39362','-listen=0','-connect=0','-dnsseed=0','-discover=0','-disablewallet','-modelnet=0','-autoupdate=0','-dbcache=4','-par=1','-server','-printtoconsole=1']
    p=subprocess.Popen(argv,env={**os.environ,'BTX035_LAB_DIR':str(state)},stdout=log,stderr=log)
    def rpc(method,params=[]):
        cookie=(node/'regtest/.cookie').read_text().strip();q=urllib.request.Request('http://127.0.0.1:39361',data=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode(),headers={'Authorization':'Basic '+base64.b64encode(cookie.encode()).decode(),'Content-Type':'application/json'})
        try:r=urllib.request.urlopen(q,timeout=20)
        except urllib.error.HTTPError as e:r=e
        d=json.load(r)
        if d.get('error'):raise RPCError(d['error']['message'])
        return d['result']
    def call(method,params,write=False):
        nonlocal counter
        params=dict(params)
        if write:counter+=1;params.update(idempotency_key=f'native-rollback-{counter:06d}',expected_state=None)
        try:
            r=rpc('lab035',[method,params]);events.append({'method':method,'result':r});return r.get('result',r)
        except Exception as e:events.append({'method':method,'error':str(e)});raise
    try:
        for _ in range(100):
            assert p.poll() is None,'node exited'
            try:info=rpc('getblockchaininfo');break
            except Exception:time.sleep(.2)
        else:raise AssertionError('startup timeout')
        assert info['chain']=='regtest'
        yield call,state
    finally:
        try:rpc('stop')
        except Exception:pass
        try:p.wait(timeout=30)
        except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=10)
        log.close();(root/'events.json').write_text(json.dumps({'binary':str(binary),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'events':events,'exit':p.returncode},indent=2)+'\n')
        # Only genesis-chain bytes from this wallet-disabled case are disposable.
        assert not list(node.rglob('wallet.dat'))
        for name in ['blocks','chainstate','indexes']:
            path=node/'regtest'/name
            if path.exists():shutil.rmtree(path)
def identity(call,label):return call('lab.identity_create',{'label':label,'recovery_key_ids':[],'recovery_threshold':1,'recovery_delay_ms':'1'},True)['record_id']
def prepare(call):return call('lab.action_prepare',{'intent_id':'a'*96},True)['one_use_permit']
def execute(call,permit):return call('lab.action_execute',{'decision_id':'b'*96,'one_use_permit':permit},True)
def fault(call,state):
    image=state/'lab.json';before=hashlib.sha256(image.read_bytes()).hexdigest();tmp=state/'lab.json.tmp';tmp.mkdir()
    try:
        with pytest.raises(RPCError,match='BTX035_RECOVERY_REQUIRED'):identity(call,'failed-unrelated')
        assert hashlib.sha256(image.read_bytes()).hexdigest()==before
    finally:tmp.rmdir()
def test_pause_survives_unrelated_failed_save_and_explicit_resume_works(lab):
    call,state=lab
    assert execute(call,prepare(call))['state']=='PERMIT_CONSUMED'
    binding=call('lab.runtime_bind',{'release_id':'b'*96,'environment_ref':{},'requested_grants':[],'assurance':'LOCAL'},True)['record_id']
    old=prepare(call)
    assert call('lab.runtime_pause',{'runtime_binding_id':binding,'reason':'operator'},True)['state']=='PAUSED'
    with pytest.raises(RPCError,match='BTX035_PAUSED'):execute(call,old)
    fault(call,state)
    with pytest.raises(RPCError,match='BTX035_PAUSED'):prepare(call)
    assert call('lab.runtime_resume',{'runtime_binding_id':binding,'new_grant_id':'a'*96},True)['state']=='RESUMED'
    with pytest.raises(RPCError):execute(call,old)
    assert execute(call,prepare(call))['state']=='PERMIT_CONSUMED'
    identity(call,'failed-unrelated')
def test_revocation_survives_unrelated_failed_save(lab):
    call,state=lab;root=identity(call,'revoked')
    req={'record_type':'Revocation','payload':{'issuer_root':root,'revocation_epoch':'1','targets':[root],'effective_after_ms':'1','reason_code':'operator','prior_revocation_id':None,'quarantine_since_ms':None},'realm_id':'a'*96,'delegation_id':None,'expires_ms':'4102444800000'}
    signed=call('lab.identity_sign',req,True)['envelope'];assert call('lab.record_verify',{'envelope':signed})['valid']
    rec=call('lab.record_import',{'envelope':signed,'publish':False},True)['record_id'];assert call('lab.identity_revoke',{'revocation_id':rec},True)['state']=='REVOKED'
    with pytest.raises(RPCError,match='BTX035_IDENTITY_REVOKED'):call('lab.identity_sign',req,True)
    fault(call,state)
    with pytest.raises(RPCError,match='BTX035_IDENTITY_REVOKED'):call('lab.identity_sign',req,True)
    assert call('lab.identity_inspect',{'principal_id':root})['state']=='REVOKED'
    identity(call,'failed-unrelated')
def test_consumed_permit_not_revived_and_failed_write_retry_works(lab):
    call,state=lab;identity(call,'ordinary');old=prepare(call)
    assert execute(call,old)['state']=='PERMIT_CONSUMED'
    with pytest.raises(RPCError,match='BTX035_REPLAY'):execute(call,old)
    fault(call,state)
    with pytest.raises(RPCError):execute(call,old)
    identity(call,'failed-unrelated')
    assert execute(call,prepare(call))['state']=='PERMIT_CONSUMED'
