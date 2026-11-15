"""Prepared, unexecuted independent-export recovery test. No action without --run."""
import argparse, base64, hashlib, json, os, pathlib, shutil, subprocess, time, urllib.request
P = pathlib.Path

def digest(path):
    h = hashlib.sha384()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()

def verify_payload(root, files):
    expected = {}
    root = root.resolve()
    for item in files:
        rel = P(item['path'])
        if rel.is_absolute() or '..' in rel.parts or str(rel) in expected:
            raise ValueError('invalid or duplicate manifest path')
        expected[str(rel)] = item
    actual = {}
    for f in root.rglob('*'):
        if f.is_symlink(): raise ValueError('payload symlink')
        if f.is_file(): actual[str(f.relative_to(root))] = f
    if set(actual) != set(expected): raise ValueError('payload file set mismatch')
    for rel, f in actual.items():
        item = expected[rel]
        if f.stat().st_size != item['size'] or digest(f) != item['sha384']:
            raise ValueError('payload size/hash mismatch: '+rel)
    return actual

REQUIRED = ('independent_copy','old_state_preserved_off_path','restore_same_identity_bytes','restart_exact_bytes_backup_intact')
def qualified(result):
    return result.get('status') == 'PASS' and result.get('cleanup') is True and not result.get('failure') and all(result.get('rows',{}).get(k) == 'PASS' for k in REQUIRED)

def verify_independent(dest, *sources):
    if dest.is_symlink(): raise ValueError('backup symlink')
    inode=(dest.stat().st_dev,dest.stat().st_ino)
    if any(inode == (s.stat().st_dev,s.stat().st_ino) for s in sources):
        raise ValueError('backup aliases source inode')

def run(args):
    root = P(args.scratch).resolve()
    if root.exists() or not str(root).startswith('/private/tmp/btx-s2-export-'):
        raise ValueError('fresh owned /tmp/btx-s2-export-* scratch required')
    if len(str(root/'m.sock').encode()) >= 100: raise ValueError('socket path too long')
    if shutil.disk_usage(root.parent).free < 1.35*1024**3: raise ValueError('need1.35GiBfree')
    manifest = json.loads(P(args.manifest).read_text())
    for name, entry in manifest['inputs'].items():
        if hashlib.sha256(P(entry['path']).read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('input hash mismatch: '+name)
    for name in ('daemon','helper','node_cli'): manifest['inputs'][name]['path']
    if not (1024 <= args.rpc_port <= 65535 and 1024 <= args.p2p_port <= 65535 and args.rpc_port != args.p2p_port):
        raise ValueError('invalid distinct ports')
    root.mkdir(); node=root/'node'; node.mkdir(); original=root/'original'; original.mkdir()
    (original/'assets').mkdir();(original/'model.safetensors').write_bytes((2).to_bytes(8,'little')+b'{}')
    (original/'assets/config.json').write_text('{}\n')
    backup=root/'backup'; backup.mkdir(); payload=backup/'payload'; payload.mkdir()
    sock=root/'m.sock'; end=time.monotonic()+900; children=[]; logs=[]; result={'status':'INCOMPLETE','rows':{},'events':[],'manifest':manifest,'limits':['tiny2filefixture','localMac','noMinIOorpeer','noinference','nohardwarelossorcrashqualification']}
    def save(): (root/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def bound(cap=30):
        if time.monotonic() >= end: raise TimeoutError('900sworkflowdeadline')
        if shutil.disk_usage(root).free < 1.25*1024**3: raise RuntimeError('diskreserve')
        if sum(p.stat().st_size for p in root.rglob('*') if p.is_file()) > 48*1024**2: raise RuntimeError('48MiBscratchcap')
        return min(cap,end-time.monotonic())
    env={k:v for k,v in os.environ.items() if k not in ('MODELD_SOCK','BTX_MODELD_SOCKET')}
    def rpc(method):
        cookie=(node/'regtest/.cookie').read_text().strip()
        req=urllib.request.Request('http://127.0.0.1:'+str(args.rpc_port),data=json.dumps({'id':1,'method':method,'params':[]}).encode(),headers={'Authorization':'Basic '+base64.b64encode(cookie.encode()).decode(),'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=bound(3)) as r: value=json.load(r)
        if value.get('error'): raise ValueError(value['error'])
        return value['result']
    def cli(stage,method,*params):
        cmd=[manifest['inputs']['node_cli']['path'],'-regtest','-datadir='+str(node),'-rpcport='+str(args.rpc_port),method]+list(params)
        done=subprocess.run(cmd,capture_output=True,text=True,env=env,cwd=root,timeout=bound())
        result['events'].append({'stage':stage,'argv':cmd,'exit':done.returncode,'stdout':done.stdout,'stderr':done.stderr});save()
        if done.returncode: raise RuntimeError('CLI failed: '+stage)
        value=json.loads(done.stdout)
        if not isinstance(value,dict) or value.get('error') or value.get('ok') is False: raise ValueError('bad CLI result: '+stage)
        return value
    def launch(name,argv):
        bound(); f=(root/(name+'.log')).open('w');logs.append(f)
        child=subprocess.Popen(argv,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT);children.append((name,child));result['events'].append({'process':name,'pid':child.pid,'argv':argv});save();return child
    def start(stage,models,existing=False):
        if existing:
            if not models.is_dir(): raise ValueError('restart modeldir missing')
        else: models.mkdir()
        helper=launch(stage+'-helper',[manifest['inputs']['helper']['path'],'-modeldir='+str(models),'-modelrpcsocket='+str(sock),'-modelstorage=8MiB','-modellandiscovery=0','-modelfollowpeers=0','-modelnatpmp=0'])
        wait=min(end,time.monotonic()+30)
        while not sock.exists():
            if helper.poll() is not None or time.monotonic()>wait: raise RuntimeError('helper readiness')
            bound();time.sleep(.1)
        daemon=launch(stage+'-node',[manifest['inputs']['daemon']['path'],'-regtest','-datadir='+str(node),'-rpcport='+str(args.rpc_port),'-port='+str(args.p2p_port),'-server','-disablewallet','-swapnet=0','-modelnet=1','-modelrpcsocket='+str(sock),'-listen=0','-connect=0','-dnsseed=0','-discover=0','-modellandiscovery=0','-modelfollowpeers=0','-dbcache=4','-par=1'])
        wait=min(end,time.monotonic()+30)
        while True:
            if daemon.poll() is not None or helper.poll() is not None: raise RuntimeError('process exit')
            try:
                if rpc('getmodelnetworkinfo').get('helper_ready') is True: break
            except (OSError,ValueError): pass
            if time.monotonic()>wait: raise TimeoutError('nodehelperreadiness')
            time.sleep(.1)
    def stop():
        live=[(n,p) for n,p in children if p.poll() is None]
        if any(n.endswith('-node') for n,p in live): rpc('stop')
        for n,p in reversed(live):
            if n.endswith('-helper'): continue
            p.wait(timeout=20)
        for n,p in live:
            if n.endswith('-helper'): p.terminate();p.wait(timeout=20)
        if sock.exists(): raise RuntimeError('helper socket not removed')
    try:
        start('source',root/'models-A')
        imp=cli('initial-import','importmodel',str(original),'{"publish":false,"pin":true}')
        export=cli('initial-export','exportmodelpath',imp['model_id']); files=export['files']
        
        if {f['path'] for f in files} != {'model.safetensors','assets/config.json'}: raise ValueError('expected both fixture files including nested config')
        source=P(export['path']).resolve()
        if not str(source).startswith(str(root/'models-A')+'/'): raise ValueError('unexpected export ownership')
        verify_payload(source,files)
        for rel,f in verify_payload(source,files).items():
            dest=payload/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dest)
            verify_independent(dest,f,original/rel)
        verify_payload(payload,files);(backup/'manifest.json').write_text(json.dumps(export,indent=2)+'\n')
        result['rows']['independent_copy']='PASS';stop()
        # Preserve rather than delete: old source/store are held off their original paths.
        original.rename(root/'preserved-original');(root/'models-A').rename(root/'preserved-models-A')
        result['rows']['old_state_preserved_off_path']='PASS'
        start('restore',root/'models-B')
        if (root/'models-B/catalog.json').exists():
            result['new_store_catalog_created_during_startup']=True
        restored=cli('restore-import','importmodel',str(payload),'{"publish":false,"pin":true}')
        for key in ('model_id','artifact_id'):
            if restored[key] != export[key]: raise ValueError('restored identity mismatch')
        restored_export=cli('restore-export','exportmodelpath',restored['model_id']);verify_payload(P(restored_export['path']),files);verify_payload(payload,files)
        result['rows']['restore_same_identity_bytes']='PASS';stop()
        # Restart the same restored modeldir; preserve all files.
        start('restart',root/'models-B',existing=True)
        final=cli('restart-export','exportmodelpath',restored['model_id']);verify_payload(P(final['path']),files);verify_payload(payload,files)
        result['rows']['restart_exact_bytes_backup_intact']='PASS';stop();result['status']='PASS'
    except Exception as exc:
        result['failure']=repr(exc);result['status']='FAIL_OR_BLOCKED'
    finally:
        cleanup=True
        try: stop()
        except Exception: cleanup=False
        for name,child in reversed(children):
            if child.poll() is None:
                child.terminate()
                try:child.wait(timeout=5)
                except subprocess.TimeoutExpired:child.kill();child.wait(timeout=5);cleanup=False
            result['events'].append({'process':name,'exit':child.returncode})
        for f in logs:f.close()
        result['cleanup']=cleanup and all(p.poll() is not None for _,p in children) and not sock.exists()
        if not qualified(result):result['status']='FAIL_OR_BLOCKED'
        save()
    print(json.dumps({'status':result['status'],'result':str(root/'result.json')}))
    return 0 if result['status']=='PASS' else 1

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true');parser.add_argument('--manifest');parser.add_argument('--scratch');parser.add_argument('--rpc-port',type=int,default=39631);parser.add_argument('--p2p-port',type=int,default=39632);args=parser.parse_args()
    if not args.run:parser.error('Prepared recipe only: --run explicitly required')
    if not args.manifest or not args.scratch:parser.error('manifest and fresh scratch required')
    raise SystemExit(run(args))
