"""Bounded positive-path ModelNet acceptance. Services run only with --run."""
import argparse, base64, hashlib, json, os, pathlib, subprocess, sys, time, unittest, shutil, urllib.request
P = pathlib.Path
FORBIDDEN = ('/.btx', '/.local/opt/', '/opt/btx', '/var/lib/btxd', '/usr/local/var/btx')
REQUIRED = ('readiness', 'doctor', 'init', 'profile', 'check', 'host', 'search', 'cleanup')
def decode_response(rc, text):
    if rc != 0: raise ValueError('command exited '+str(rc))
    value = json.loads(text)
    if not isinstance(value, dict) or value.get('ok') is False or value.get('error'): raise ValueError('command returned an error or non-object')
    def visit(obj):
        if isinstance(obj, dict):
            if obj.get('wallet_signed') is True or obj.get('runtime_started') is True or obj.get('runtime_exec') is True: raise ValueError('unexpected wallet/runtime action')
            if 'automatic_spend_atoms' in obj and obj['automatic_spend_atoms'] not in (0, '0'): raise ValueError('unexpected spending')
            for child in obj.values(): visit(child)
        elif isinstance(obj, list):
            for child in obj: visit(child)
    visit(value)
    return value

def verdict(rows):
    return 'PASS' if all(rows.get(name, {}).get('status') == 'PASS' for name in REQUIRED) else 'FAILED_OR_BLOCKED'

class OfflineControls(unittest.TestCase):
    def test_init_false(self): self.assertRaises(ValueError, validate_row, 'init', {'initialized':False})
    def test_host_identity_missing(self): self.assertRaises(ValueError, validate_row, 'host', {'ok':True})
    def test_host_identity_valid(self): self.assertEqual(validate_row('host', {'model_id':'test'}), {'model_id':'test'})
    def test_global_coverage(self): self.assertRaises(ValueError, validate_row, 'search', {'coverage_complete':True})
    def test_valid_json(self): self.assertEqual(decode_response(0, '{"initialized":true}'), {'initialized':True})
    def test_nonzero_fails(self): self.assertRaises(ValueError, decode_response, 1, '{"ok":true}')
    def test_error_fails(self): self.assertRaises(ValueError, decode_response, 0, '{"ok":false}')
    def test_bad_json_fails(self): self.assertRaises(ValueError, decode_response, 0, 'not json')
    def test_missing_core_not_pass(self): self.assertEqual(verdict({}), 'FAILED_OR_BLOCKED')
    def test_skip_not_pass(self): self.assertEqual(verdict({k:{'status':'SKIPPED'} for k in REQUIRED}), 'FAILED_OR_BLOCKED')
    def test_timeout_not_pass(self): self.assertEqual(verdict({k:{'status':'TIMEOUT'} for k in REQUIRED}), 'FAILED_OR_BLOCKED')
    def test_complete_pass(self): self.assertEqual(verdict({k:{'status':'PASS'} for k in REQUIRED}), 'PASS')
    def test_unexpected_runtime(self): self.assertRaises(ValueError, decode_response, 0, '{"runtime_started":true}')

def validate_row(label, value):
    if label == 'init' and value.get('initialized') is not True:
        raise ValueError('init did not initialize identity')
    if label == 'host':
        nested = value.get('result', {})
        identity = value.get('uri') or value.get('model_id') or (nested.get('uri') or nested.get('model_id') if isinstance(nested, dict) else None)
        if not isinstance(identity, str) or not identity:
            raise ValueError('host returned no model identity; inspect schema before proceeding')
    if label == 'search' and value.get('coverage_complete') is True:
        raise ValueError('search incorrectly claims complete global coverage')
    return value

def run(args):
    if not 1 <= args.deadline <= 900: raise ValueError('deadline must be 1..900 seconds')
    if not (1024 <= args.rpc_port <= 65535 and 1024 <= args.p2p_port <= 65535 and args.rpc_port != args.p2p_port): raise ValueError('invalid distinct ports')
    if shutil.disk_usage('.').free < 1.30*1024**3: raise ValueError('insufficient reserve for bounded runtime')
    manifest=json.loads(P(args.manifest).read_text()); root=P(args.scratch).resolve()
    if root.exists() or any(x in str(root) for x in FORBIDDEN) or not str(root).startswith('/private/tmp/btx-s2-first-run-'):
        raise ValueError('scratch must be a fresh owned /tmp/btx-s2-first-run-* directory')
    if len(str(root/'m.sock').encode())>=100: raise ValueError('socket path too long')
    for name,item in manifest['inputs'].items():
        path=P(item['path']); assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256'],name
    root.mkdir(); node=root/'node'; model=root/'models'; host=root/'host-ops';node.mkdir();model.mkdir();host.mkdir()
    (host/'model.safetensors').write_bytes((2).to_bytes(8,'little')+b'{}')
    (host/'README.md').write_text('btx-model host ops unique sidecar\n')
    sock=root/'m.sock'; rows={k:{'status':'BLOCKED'} for k in REQUIRED};events=[];children=[];logs=[];end=time.monotonic()+args.deadline
    result={'profile':'positive first-run subset; reused949 binaries and main074 CLI source','rows':rows,'events':events,'source':manifest['source'],'archive_sha256':manifest['archive_sha256'],'omitted':manifest['omitted'],'restart_tested':False}
    def save(): (root/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def timeout(cap=30):
        left=end-time.monotonic()
        if sum(p.stat().st_size for p in root.rglob('*') if p.is_file()) > 50*1024**2: raise RuntimeError('runtime evidence exceeded 50 MiB budget')
        if shutil.disk_usage(root).free < 1.25*1024**3: raise RuntimeError('disk reserve reached')
        if left<=0: raise TimeoutError('whole workflow deadline')
        return min(cap,left)
    env={k:v for k,v in os.environ.items() if k not in ('MODELD_SOCK','BTX_MODELD_SOCKET')};env['BTX_OPENSSL']=manifest['openssl']
    def cli(label,verb):
        cmd=[sys.executable,manifest['inputs']['cli_script']['path'],'--socket',str(sock),'--json']+verb
        entry={'row':label,'argv':cmd};events.append(entry);save()
        try:
            done=subprocess.run(cmd,cwd=root,env=env,capture_output=True,text=True,timeout=timeout());entry.update(returncode=done.returncode,stdout=done.stdout,stderr=done.stderr)
            value=validate_row(label,decode_response(done.returncode,done.stdout));rows[label]={'status':'PASS','value':value};save();return value
        except subprocess.TimeoutExpired:
            rows[label]={'status':'TIMEOUT'};save();raise
        except Exception as exc:
            rows[label]={'status':'FAIL','error':str(exc)};save();raise
    def launch(name,argv):
        f=(root/(name+'.log')).open('w');logs.append(f);proc=subprocess.Popen(argv,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT);children.append((name,proc));events.append({'process':name,'pid':proc.pid,'argv':argv});save();return proc
    def rpc(method):
        cookie=(node/'regtest/.cookie').read_text().strip();data=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':[]}).encode();req=urllib.request.Request('http://127.0.0.1:'+str(args.rpc_port),data=data,headers={'Authorization':'Basic '+base64.b64encode(cookie.encode()).decode(),'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=timeout(3)) as response: out=json.load(response)
        if out.get('error'): raise ValueError(out['error'])
        return out['result']
    try:
        helper=launch('helper',[manifest['inputs']['helper']['path'],'-modeldir='+str(model),'-modelrpcsocket='+str(sock),'-modelstorage=8MiB','-modellandiscovery=0','-modelfollowpeers=0','-modelnatpmp=0'])
        ready_end=min(end,time.monotonic()+30)
        while not sock.exists():
            if helper.poll() is not None or time.monotonic()>ready_end: raise RuntimeError('helper socket not ready')
            time.sleep(.1)
        daemon=launch('node',[manifest['inputs']['daemon']['path'],'-regtest','-datadir='+str(node),'-rpcport='+str(args.rpc_port),'-port='+str(args.p2p_port),'-listen=0','-connect=0','-dnsseed=0','-discover=0','-disablewallet','-swapnet=0','-modelnet=1','-modelrpcsocket='+str(sock),'-modellandiscovery=0','-modelfollowpeers=0','-dbcache=4','-par=1','-server'])
        ready_end=min(end,time.monotonic()+30)
        while True:
            if daemon.poll() is not None or helper.poll() is not None: raise RuntimeError('test process exited')
            try:
                info=rpc('getmodelnetworkinfo')
                if info.get('helper_ready') is True: break
            except (OSError,ValueError): pass
            if time.monotonic()>ready_end: raise TimeoutError('node/helper readiness deadline')
            time.sleep(.2)
        rows['readiness']={'status':'PASS','value':info};save()
        cli('doctor',['doctor']);cli('init',['init'])
        cli('profile',['profile','show']);cli('check',['check',str(host/'model.safetensors')]);hosted=cli('host',['host',str(host)]);result['host_response']=hosted
        cli('search',['search','ops','--scope','LOCAL']);result['search_limit']='Response execution/metadata checked; exact hosted identity match must be assessed from raw data.'
    except Exception as exc:
        result['failure']=repr(exc)
    finally:
        try:
            if any(name=='node' and p.poll() is None for name,p in children): rpc('stop')
        except Exception: pass
        cleanup=True
        for name,proc in reversed(children):
            if proc.poll() is None:
                if name!='node': proc.terminate()
                try: proc.wait(timeout=20)
                except subprocess.TimeoutExpired: proc.kill();proc.wait(timeout=5);cleanup=False
            events.append({'process':name,'exit':proc.returncode})
        for f in logs:f.close()
        rows['cleanup']={'status':'PASS' if cleanup else 'FAIL'}
        result['verdict']=verdict(rows) if not result.get('failure') else 'FAILED_OR_BLOCKED';save()
    print(json.dumps({'result':str(root/'result.json'),'verdict':result['verdict']}));return 0 if result['verdict']=='PASS' else 1

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--self-test',action='store_true');parser.add_argument('--run',action='store_true');parser.add_argument('--manifest');parser.add_argument('--scratch');parser.add_argument('--rpc-port',type=int,default=39621);parser.add_argument('--p2p-port',type=int,default=39622);parser.add_argument('--deadline',type=int,default=900);args=parser.parse_args()
    if args.self_test:
        outcome=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(OfflineControls));return 0 if outcome.wasSuccessful() else 1
    if not args.run:parser.error('No services start unless --run is explicitly selected')
    if not args.manifest or not args.scratch:parser.error('--manifest and --scratch are required')
    return run(args)
if __name__=='__main__':sys.exit(main())
