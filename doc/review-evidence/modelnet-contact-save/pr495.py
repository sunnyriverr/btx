"""Same full-catalog upgrade/restart journey against exact stock and #495 helpers."""
from pathlib import Path
import hashlib, json, os, shutil, signal, socket, subprocess, tempfile, time

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
VALID = ['[::1]:42000'] + ['127.0.0.1:'+str(42000+i) for i in range(1,63)]
BAD = 'zz'
REPLACEMENT = '127.0.0.1:42900'
OVERFLOW = '127.0.0.1:42901'
CANCELLED = False

class Helper:
    def __init__(self,binary,root,out,label):
        self.binary=binary.resolve(); self.root=root; self.out=out; self.label=label
        self.store=root/'store'; self.store.mkdir(parents=True,exist_ok=True)
        self.sock=root/'rpc.sock'; self.proc=None; self.log=None; self.seq=0; self.starts=0
        self.cleanup_signals=[]
    def start(self):
        assert self.proc is None and not self.sock.exists()
        self.starts+=1; self.log=(self.out/(self.label+'-'+str(self.starts)+'.log')).open('wb')
        home=self.root/'home';home.mkdir(exist_ok=True)
        args=[str(self.binary),'-modeldir='+str(self.store),'-modelrpcsocket='+str(self.sock),
              '-modelstorage=8MiB','-modellandiscovery=0','-modelfollowpeers=0','-modelnatpmp=0',
              '-modelhost=0','-modelseed=off','-pwcchain=regtest']
        self.proc=subprocess.Popen(args,env=dict(os.environ,HOME=str(home),XDG_DATA_HOME=str(home/'data'),
                                                XDG_RUNTIME_DIR=str(self.root)),
                                   stdout=self.log,stderr=subprocess.STDOUT,start_new_session=True)
        deadline=time.monotonic()+30
        while not self.sock.exists():
            assert self.proc.poll() is None and time.monotonic()<deadline,'helper startup failed'
            time.sleep(.1)
        assert Path('/proc/'+str(self.proc.pid)+'/exe').resolve()==self.binary
        info=self.rpc('getmodelnetworkinfo',[])
        assert info['follow_configured_peers'] is False,info
    def rpc(self,method,params):
        self.seq+=1
        req={'jsonrpc':'1.0','id':self.seq,'method':method,'params':params}
        with socket.socket(socket.AF_UNIX) as client:
            client.settimeout(10);client.connect(str(self.sock))
            client.sendall(json.dumps(req).encode()+b'\n');client.shutdown(socket.SHUT_WR)
            with client.makefile('rb') as stream: raw=stream.read(1024*1024+1)
        assert len(raw)<=1024*1024
        answer=json.loads(raw)
        assert answer['id']==self.seq and answer['error'] is None,(method,answer)
        return answer['result']
    def peers(self): return self.rpc('getmodelpeers',[])['peers']
    def add(self,peer):
        answer=self.rpc('addmodelnode',[peer]);assert answer['automatic_spend_atoms']==0
        return answer
    def disk_peers(self): return json.loads((self.store/'catalog.json').read_text())['peers']
    def stop(self):
        if self.proc is None:return
        assert self.proc.poll() is None,'helper exited unexpectedly'
        self.proc.send_signal(signal.SIGTERM);self.proc.wait(timeout=25)
        assert self.proc.returncode==0 and not self.sock.exists()
        self.proc=None;self.log.close();self.log=None
    def cleanup(self):
        try:self.stop()
        finally:
            if self.proc is not None and self.proc.poll() is None:
                self.cleanup_signals.append('SIGKILL');os.killpg(self.proc.pid,signal.SIGKILL)
                self.proc.wait(timeout=10)
            if self.log:self.log.close()
            assert self.proc is None or self.proc.poll() is not None
            shutil.rmtree(self.root)

def journey(binary,seed,out,label):
    """Identical calls and evaluation for each binary; baseline failure is retained."""
    root=Path(tempfile.mkdtemp(prefix='peer495-')); helper=Helper(binary,root,out,label)
    result={'binary_sha256':sha(binary),'seed_sha256':sha(seed)}
    try:
        shutil.copy2(seed,helper.store/'catalog.json')
        assert sha(helper.store/'catalog.json')==sha(seed)
        helper.start();initial=helper.peers();result['initial_peers']=initial
        result['valid_contacts_preserved_on_load']=set(VALID)<=set(initial) and len(initial)==len(set(initial))
        result['old_bad_contact_removed']=BAD not in initial
        bad_before=helper.add(BAD);result['bad_reply_before_refill']=bad_before
        result['bad_refused_with_free_slot']=(bad_before['ok'] is False
            and bad_before.get('reason')=='endpoint must be host:port' and helper.peers()==initial)
        answer=helper.add(REPLACEMENT);result['replacement_reply']=answer
        live=helper.peers();result['peers_after_replacement']=live
        result['replacement_usable']=answer['ok'] is True and REPLACEMENT in live
        # Duplicate handling must be idempotent even when the list is full.
        duplicate=helper.add(VALID[0]);result['duplicate_reply']=duplicate
        result['duplicate_idempotent']=duplicate['ok'] is True and helper.peers()==live
        overflow=helper.add(OVERFLOW);result['overflow_reply']=overflow
        result['cap_enforced']=overflow['ok'] is False and overflow['reason']=='peer list full' and helper.peers()==live
        result['persisted_peers_before_restart']=helper.disk_peers()
        helper.stop();helper.start();restarted=helper.peers()
        result['peers_after_restart']=restarted
        result['restart_state_preserved']=restarted==live==helper.disk_peers()
        result['valid_contacts_preserved_after_restart']=set(VALID)<=set(restarted)
        result['exact_recovered_catalog']=set(restarted)==set(VALID+[REPLACEMENT]) and len(restarted)==64
        # Observe the documented invalid-input reason independently of capacity.
        bad=helper.add(BAD);result['bad_reply_after_restart']=bad
        result['bad_refused']=(bad['ok'] is False and bad.get('reason')=='endpoint must be host:port'
                               and helper.peers()==restarted)
        result['responsive_after_restart']=isinstance(helper.rpc('getmodelnetworkinfo',[]),dict)
        helper.stop();result['clean_shutdown']=True
        required=['valid_contacts_preserved_on_load','old_bad_contact_removed','bad_refused_with_free_slot','replacement_usable',
                  'duplicate_idempotent','cap_enforced','restart_state_preserved',
                  'valid_contacts_preserved_after_restart','exact_recovered_catalog','bad_refused',
                  'responsive_after_restart','clean_shutdown']
        result['recovery_pass']=all(result[x] for x in required)
        result['failed_acceptance']=[x for x in required if not result[x]]
    except Exception as error:result.update(error=repr(error),recovery_pass=False)
    finally:
        try:helper.cleanup()
        except Exception as error:result['cleanup_error']=repr(error)
        result.update(cleanup_signals=helper.cleanup_signals,owned_runtime_removed=not root.exists())
    return result

def main():
    def interrupted(signum,frame):
        global CANCELLED
        CANCELLED=True
        raise TimeoutError('owned native journey interrupted')
    signal.signal(signal.SIGTERM,interrupted)
    w=Path(os.environ['GITHUB_WORKSPACE']);out=w/'pr495-records';out.mkdir(exist_ok=True)
    build=json.loads((out/'build-result.json').read_text());assert build['passed']
    result={'profile':'Ubuntu 22.04 x86_64, GCC11.4, retained OpenSSL3.5.9; real helper Unix RPC',
            'scope':'Contact catalog admission, capacity, clean restart; loopback contacts only; no transport qualification, node, wallet or inference',
            'variants':{}}
    for label in ('base','candidate'):
        binary=w/'pr495-binaries'/label
        assert sha(binary)==build['binaries'][label];binary.chmod(0o755)
    root=Path(tempfile.mkdtemp(prefix='seed495-'));seed_helper=Helper(w/'pr495-binaries/base',root,out,'seed')
    try:
        seed_helper.start();assert seed_helper.peers()==[]
        for endpoint in VALID+[BAD]:assert seed_helper.add(endpoint)['ok'] is True
        assert seed_helper.peers()==VALID+[BAD]
        assert seed_helper.disk_peers()==VALID+[BAD]
        seed_helper.stop()
        seed=out/'old-full-catalog.json';shutil.copy2(seed_helper.store/'catalog.json',seed)
        result['seed']={'sha256':sha(seed),'count':64,'valid':63,'invalid':1,'created_by_stock_rpc':True}
    except Exception as error:result['seed_error']=repr(error)
    finally:
        seed_helper.cleanup();result['seed_runtime_removed']=not root.exists()
    if 'seed' in result:
        for label in ('base','candidate'):
            if CANCELLED:
                result['cancelled']=True
                break
            result['variants'][label]=journey(w/'pr495-binaries'/label,seed,out,label)
            (out/'recovery-result.json').write_text(json.dumps(result,indent=2)+'\n')
    base=result['variants'].get('base',{});candidate=result['variants'].get('candidate',{})
    result['matched_before_after']=bool(not base.get('recovery_pass',True) and candidate.get('recovery_pass'))
    result['baseline_failure_is_capacity']=bool(base.get('replacement_reply',{}).get('reason')=='peer list full'
        and base.get('initial_peers')==VALID+[BAD] and 'error' not in base)
    result['passed']=all([result['matched_before_after'],result['baseline_failure_is_capacity'],
                          result.get('seed_runtime_removed'),base.get('owned_runtime_removed'),
                          candidate.get('owned_runtime_removed'),not base.get('cleanup_signals'),
                          not candidate.get('cleanup_signals')])
    (out/'recovery-result.json').write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
