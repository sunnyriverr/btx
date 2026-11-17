"""Prepared normal-helper test; no native execution at import time."""
import argparse, errno, os, hashlib, json, math, signal, socket, struct, shutil, tempfile, time
from pathlib import Path
from helpers import Helper, completion, digest, require, UPLOAD_BPS
from classify import classify
PRIOR_HASH='33d02aaa7300fabeedf08d2bbb09f52af91e6462b3f90098ce0c4ec1f2b49cb6'
EXPECTED='ddbdfdfacbbf305f1a4e85f9e2ffbabefb79e43e3c260452162b6a4d525e85bf'
SIZE=16 << 20

def make_model(path):
    header=json.dumps({'t':{'dtype':'U8','shape':[SIZE],'data_offsets':[0,SIZE]}},separators=(',',':')).encode()
    with path.open('wb') as f:
        f.write(struct.pack('<Q',len(header))+header)
        for n in range(16):f.write(hashlib.shake_256(f'retrieval-control:{n}'.encode()).digest(1 << 20))

def saved(path, job):
    if not path.exists():return False
    return any(x.get('job_id')==job for x in json.loads(path.read_text()).get('jobs',[]))

def verify_pieces(model, pieces):
    with model.open('rb') as f:
        for name, meta in pieces.items():
            f.seek(int(name.removesuffix('.piece'))*(4 << 20));b=f.read(4 << 20)
            require(len(b)==meta['bytes'] and hashlib.sha256(b).hexdigest()==meta['sha256'],'piece identity')

def wait_for(fn, seconds, message):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        result=fn()
        if result:return result
        time.sleep(1)
    raise RuntimeError(message)

def admit_source(receipt):
    expected={
        'jobs':'7c58184f60d414f45cc1a1c52bb7d8db51b2d1cb9bdb37b495dc566acbd706cd',
        'cancel':'046750f293e859affe51b0d1f01fee9e0afe8c15eaa4c5c7cf0bd5f7835d76a2',
        'atomic_json_write':'92769e97a880715e6926d5f2d420c3560c76cfc2ebdd7fb55d02ae31c5f4f91b',
    }
    spans=receipt.get('source_spans',{})
    return (receipt.get('helper_sha256')==EXPECTED and receipt.get('source_producer_hash_verified') is True
            and set(spans)==set(expected)
            and all(spans[n].get('equal') is True and spans[n].get('retained_sha256')==h
                    and spans[n].get('current_sha256')==h for n,h in expected.items()))

def cleanup_helpers(helpers):
    errors=[]
    for h in reversed(helpers):
        try:
            h.cleanup()
        except Exception as exc:
            errors.append({'helper':h.label,'error':repr(exc)})
            # Still attempt cleanup of every owned process, even if a receipt write failed.
            try:
                if h.proc is not None and h.proc.poll() is None:
                    os.killpg(h.proc.pid,signal.SIGTERM)
                    try:h.proc.wait(10)
                    except Exception:
                        os.killpg(h.proc.pid,signal.SIGKILL);h.proc.wait(10);h.forced=True
            except Exception as stop_error:
                errors.append({'helper':h.label,'stop_error':repr(stop_error)})
    stopped=all(h.proc is None or h.proc.poll() is not None for h in helpers)
    clean=stopped and not errors and all(not h.forced and not h.cleanup_error for h in helpers)
    return clean,stopped,errors

def remove_stopped_runtime(root,stopped):
    if root is None or not stopped:return False
    shutil.rmtree(root)
    return True

def load_healthy_receipt(path):
    require(digest(path)==PRIOR_HASH,'prior observation identity')
    prior=json.loads(path.read_text());c=prior['cases']['healthy']
    require(prior['binary_verified'] is True and prior['source_verified'] is True and prior['clean_cleanup'] is True,'prior provenance/cleanup')
    require(all(c[k] is True for k in ('persisted_active','partial_verified','cancelled_live','clean_stop','pieces_preserved','saved_job_removed','reopen_ready','quiet_window_complete')),'prior healthy control incomplete')
    require(c['resumed'] is False and c['new_verified_piece'] is False,'prior healthy control resumed')
    c['reused_from_run']=44060423258
    c['scope_note']='Original128KiB/s healthy control, same verified helper/source; not repeated at the new512KiB/s diagnostic-fixture pace.'
    return c

def sample_transfer(receiver,provider,job):
    snapshot={}
    try:snapshot['job']=receiver.job(job)
    except Exception as exc:snapshot['job_error']=repr(exc)
    try:
        info=provider.info()
        snapshot['provider']={k:info.get(k) for k in ('upload_limit','active_transfers','direct_bytes','helper_ready','pq1_ready')}
    except Exception as exc:snapshot['provider_error']=repr(exc)
    return snapshot

def observe(binary,out,source_verified,healthy):
    out.mkdir(parents=True,exist_ok=False)
    r={'complete':False,'cases':{'healthy':healthy},'healthy_reused_from_run':44060423258,'source_verified':source_verified,'binary_verified':digest(binary)==EXPECTED,'origin_verified':False,'clean_cleanup':False,'completion_exact':False}
    helpers=[];faults=[];runtime_root=None;start=time.monotonic()
    def record():
        r['seconds']=time.monotonic()-start
        (out/'observations.json').write_text(json.dumps(r,indent=2)+'\n')
    def alarm(*_):raise TimeoutError('20 minute observation bound')
    signal.signal(signal.SIGALRM,alarm);signal.alarm(1200)
    try:
        require(r['binary_verified'] and source_verified,'binary/source provenance gate')
        runtime_root=Path(tempfile.mkdtemp(prefix="s2-retrieval-control-"))
        root=runtime_root;model=root/'model.safetensors';make_model(model);expected=digest(model,'sha384');total_pieces=math.ceil(model.stat().st_size/(4 << 20))
        def new_provider(label):
            with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            provider=Helper(binary,root/('provider-'+label),out,'provider-'+label,64 << 20,hostport=port)
            helpers.append(provider);provider.start()
            imported=provider.ok('importmodel',[str(model),{'pin':True}]);require(imported.get('seeded') is True,'source not serving')
            require(provider.info()['upload_limit']==UPLOAD_BPS,'provider pacing configuration')
            r['origin_verified']=True;record()
            return provider,port,imported['uri'],imported['artifact_id']
        for name in ['recovered_before_stop','fault_through_stop']:
            print('CASE '+name,flush=True)
            provider,port,uri,artifact=new_provider(name)
            c={};r['cases'][name]=c
            recv=Helper(binary,root/name,out,name,64 << 20,peer=f'127.0.0.1:{port}');helpers.append(recv);recv.start()
            job,answer=recv.request(uri);require(bool(job),'no native job');c['job_id']=job;c['getmodel_response']=answer
            state=recv.store/'retrieve_jobs.json';fault=recv.store/'retrieve_jobs.json.tmp'
            wait_for(lambda:saved(state,job),10,'job not persisted');c['persisted_active']=True
            c['waiting_snapshots']=[]
            def partial_piece():
                snap=sample_transfer(recv,provider,job);c['waiting_snapshots'].append(snap);record()
                status=snap.get('job',{}).get('status')
                require(status not in ('done','failed','cancelled'),'job ended before partial-piece gate: '+json.dumps(snap))
                return recv.pieces(artifact)
            initial=wait_for(partial_piece,75,'no verified partial piece before timeout');verify_pieces(model,initial)
            print('PARTIAL '+name,flush=True)
            require(len(initial)<total_pieces and recv.job(job)['status'] in ('queued','running'),'job completed before cancellation')
            c['partial_verified']=True;c['before_cancel_pieces']=initial;before=state.read_bytes();c['saved_before_sha256']=digest(state)
            if name!='healthy':
                require(not fault.exists(),'unexpected existing temporary path');fault.mkdir();faults.append(fault);c['fault_present_at_cancel']=fault.is_dir()
                try:
                    with fault.open('wb'):pass
                except IsADirectoryError as e:c['probe_is_directory']=e.errno==errno.EISDIR
                require(c.get('probe_is_directory') is True,'fault probe did not reach directory error')
            reply=recv.rpc('cancelmodeljob',[job]);c['cancel_reply']=reply;c['rpc_error']=reply.get('error')
            result=reply.get('result') or {};c['cancelled_live']=result.get('cancelled') is True
            error=c['rpc_error'] or {};message=str(error.get('message','')) if isinstance(error,dict) else str(error);code=error.get('code') if isinstance(error,dict) else None
            c['persistence_error']=bool(error) and (code in ('IO','IO_ERROR') or ('retrieve_jobs' in message and any(w in message.lower()for w in ('write','save','rename'))));c['old_file_preserved_on_cancel']=state.read_bytes()==before
            record()
            if name=='recovered_before_stop':fault.rmdir()
            recv.stop();c['clean_stop']=True
            stopped=recv.pieces(artifact);verify_pieces(model,stopped);c['after_stop_pieces']=stopped
            require(len(stopped)<total_pieces,'completed before stop; observation not discriminating')
            c['pieces_preserved']=all(k in stopped and stopped[k]['sha256']==v['sha256']for k,v in initial.items())
            c['old_file_preserved_on_stop']=state.read_bytes()==before
            c['fault_present_through_stop']=fault.is_dir()
            if name=='fault_through_stop':require(fault.is_dir(),'fault disappeared during stop');fault.rmdir();c['fault_cleared_before_reopen']=not fault.exists()
            c['saved_job_removed']=not saved(state,job)
            logs='\n'.join(p.read_text(errors='replace')for p in out.glob(name+'-*.log'))
            c['persistence_warning']=any('retrieve_jobs' in line and any(w in line.lower()for w in ['error','fail','cannot','unable'])for line in logs.splitlines())
            require(provider.proc.poll() is None,'provider exited');c['origin_still_alive']=True
            recv.start();c['reopen_ready']=True;c['new_verified_piece']=False;c['resumed']=False;c['quiet_window_complete']=False
            end=time.monotonic()+(75 if name=='fault_through_stop'else 12)
            while time.monotonic()<end:
                current=recv.pieces(artifact);verify_pieces(model,current)
                new={k:v for k,v in current.items()if k not in stopped}
                if new:
                    c.update(new_verified_piece=True,resumed=True,after_reopen_pieces=current);break
                # Capture status for context; it is not sufficient evidence of resumed work.
                c['reopened_job']=recv.job(job);time.sleep(.5)
            else:c['quiet_window_complete']=True
            recv.stop();provider.stop();record()
        # Independent fresh provider avoids paced state leaking across cases.
        print("CASE completion",flush=True)
        provider,port,uri,artifact=new_provider("completion")
        control=Helper(binary,root/'completion',out,'completion',64 << 20,peer=f'127.0.0.1:{port}');helpers.append(control);control.start();job,_=control.request(uri);row=control.settled(job,240);require(row['status']=='done','uncancelled completion failed');r['completion']=completion(control,uri,expected);r['completion_exact']=True;control.stop();provider.stop()
        r['complete']=True
    except Exception as e:
        import traceback;r['setup_or_observation_error']=traceback.format_exc()
    finally:
        signal.alarm(0)
        clean,stopped,errors=cleanup_helpers(helpers)
        if runtime_root is not None and stopped:
            try:remove_stopped_runtime(runtime_root,stopped)
            except Exception as exc:errors.append({'temporary_cleanup_error':repr(exc)});clean=False
        elif runtime_root is not None:
            r['preserved_runtime_root']=str(runtime_root)
        r['cleanup_errors']=errors
        r['clean_cleanup']=clean
        r['verdict']=classify(r) if r['complete'] else 'INCONCLUSIVE';record()
    return r

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--helper',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--source-receipt',type=Path,required=True);ap.add_argument('--healthy-receipt',type=Path,required=True);a=ap.parse_args()
    receipt=json.loads(a.source_receipt.read_text());require(admit_source(receipt),'source receipt mismatch')
    healthy=load_healthy_receipt(a.healthy_receipt)
    result=observe(a.helper.resolve(),a.out.resolve(),True,healthy);print(result['verdict']);raise SystemExit(0 if result['complete'] and result['verdict']!='INCONCLUSIVE'else 2)
