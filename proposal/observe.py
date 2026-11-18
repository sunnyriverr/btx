"""Observe ordinary canonical document materialization; no product changes.

Only accept a race when an actual regular destination file was observed while
execute remained outstanding, cancellation returned CANCELLED before execute
returned, and a later independent get reports MODEL_READY. Files may remain:
this test asserts no undocumented delete-on-cancel promise.
"""
import argparse,copy,hashlib,json,socket,struct,tempfile,threading,time,traceback
from pathlib import Path
from fixture import Fixture
SHA='28d7ecb6c611e5676d85de7a64038bc7d07cd0b6b2fb2606390d5e6405838ad2'
def digest(b):return hashlib.sha384(b).hexdigest()
def classify(r):
    assert r['complete'] and r['clean_shutdown'] and r['controls']['normal'] and r['controls']['cancel_before_start']
    assert r['helper_sha256']==SHA and r['originals_unchanged']
    proven=[]
    for q in r['attempts']:
        if q.get('error'): raise AssertionError(q['error'])
        if q.get('copy_seen') and q['cancel']['cancelled'] and q['cancel']['state']=='CANCELLED' and q['cancel_returned']<q['execute_returned'] and q['final']['state']=='MODEL_READY':proven.append(q['index'])
    return {'verdict':'CANCELLATION_OVERWRITTEN' if proven else 'RACE_NOT_OBSERVED','proven_attempts':proven}
def main():
    p=argparse.ArgumentParser();p.add_argument('--helper',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    r={'complete':False,'controls':{},'attempts':[],'scope':'Canonical unsigned REGTEST package documents; real local helper and regular files. Not model weights, swarm transfer, node, inference or other platforms.','helper_sha256':hashlib.sha256(args.helper.read_bytes()).hexdigest()};f=None
    try:
        assert r['helper_sha256']==SHA
        with tempfile.TemporaryDirectory(prefix='acq-cancel-',dir='/tmp') as tmp:
            root=Path(tmp);f=Fixture(args.helper.resolve(),root,args.out);src=root/'source';src.mkdir()
            payload=json.loads(Path(__file__).with_name('package.json').read_text())
            # Retain the existing valid AGENTS/README/runtime guidance. Add ordinary
            # UTF-8 package documents within 32-document and 256KiB aggregate caps.
            docs=payload['core']['documents']; total=sum(int(d['size_bytes'])for d in docs)
            for i in range(29):
                text=(f'Package test document {i}\n'+'D'*8000+'\n');b=text.encode();total+=len(b)
                docs.append({'path':f'doc{i:02}.txt','media_type':'text/plain','encoding':'utf-8','text':text,'size_bytes':str(len(b)),'sha384':digest(b)})
            assert len(docs)==32 and total<=262144
            docs.sort(key=lambda d:d['path'].encode('ascii'))
            files=[];original={}
            for d in docs:
                path=src/d['path'];path.parent.mkdir(exist_ok=True,parents=True);path.write_text(d['text']);assert digest(path.read_bytes())==d['sha384'];original[str(path)]=digest(path.read_bytes());files.append({'path':d['path'],'sha384':d['sha384'],'source_path':str(path)})
            # A genuinely imported local test model supplies the resource identity;
            # package docs are copied, not falsely labelled as model weights.
            model=root/'small.safetensors';header=json.dumps({'w':{'dtype':'U8','shape':[128],'data_offsets':[0,128]}},separators=(',',':')).encode();model.write_bytes(struct.pack('<Q',120)+header.ljust(120,b' ')+b'M'*128)
            with f.running():
                imported=f.ok('importmodel',str(model),{'pin':True,'publish':False});r['import']=imported;mid=imported['model_id'];assert len(mid)==96
                core=payload['core'];core['resources'][0]['id']=mid;core['resources'][0].pop('manifest_id',None);core['resources'][0]['format']='SAFETENSORS';core['resources'][0]['size_bytes']=str(model.stat().st_size);core['variants'][0]['resource_id']=mid;core['variants'][0]['format']='SAFETENSORS'
                built=f.ok('createbtxpackage',{'payload':payload,'core_version':2});r['package']={k:v for k,v in built.items()if k!='hex'}
                def plan(label):
                    dest=root/label;q=f.ok('planbtxacquisition',{'hex':built['hex'],'local_policy':{'destination':str(dest),'explicit_variant':'demo-q4'}});return dest,q['plan_id']
                def req(pid):return {'plan_id':pid,'verified_local_files':files}
                def exact(dest):return all((dest/d['path']).is_file() and digest((dest/d['path']).read_bytes())==d['sha384']for d in docs)
                dest,pid=plan('normal');normal=f.ok('executebtxacquisition',req(pid));r['normal']=normal;r['controls']['normal']=normal['state']=='MODEL_READY'and normal['file_bytes_verified']and exact(dest);assert r['controls']['normal'];f.ok('cancelbtxacquisition',{'plan_id':pid})
                dest,pid=plan('pre-cancel');cancel=f.ok('cancelbtxacquisition',{'plan_id':pid});denied=f.rpc('executebtxacquisition',req(pid));r['pre_cancel']={'cancel':cancel,'execute':denied};r['controls']['cancel_before_start']=cancel['state']=='CANCELLED'and denied.get('error')is not None and not dest.exists();assert r['controls']['cancel_before_start']
                for i in range(5):
                    dest,pid=plan('copy-'+str(i));q={'index':i};r['attempts'].append(q);done=threading.Event()
                    def execute():
                        try:q['execute']=f.ok('executebtxacquisition',req(pid))
                        except Exception:q['error']=traceback.format_exc()
                        finally:q['execute_returned']=time.monotonic();done.set()
                    thread=threading.Thread(target=execute,daemon=True);q['started']=time.monotonic();thread.start()
                    try:
                        deadline=time.monotonic()+5
                        while not done.is_set() and time.monotonic()<deadline:
                            # Real output presence, not a sleep assumed to mean copying.
                            if (dest/'AGENTS.md').is_file():
                                q['copy_seen']=time.monotonic();q['observed_bytes']=(dest/'AGENTS.md').stat().st_size
                                q['cancel']=f.ok('cancelbtxacquisition',{'plan_id':pid});q['cancel_returned']=time.monotonic();break
                            time.sleep(.0001)
                    finally:thread.join(15);assert not thread.is_alive(),'copy thread exceeded bound'
                    if q.get('error'):raise AssertionError(q['error'])
                    q['final']=f.ok('getbtxacquisition',{'plan_id':pid});q['exact_bytes']=exact(dest);assert q['exact_bytes']
                    # Release the finished plan's local lease using ordinary RPC.
                    f.ok('cancelbtxacquisition',{'plan_id':pid})
                r['originals_unchanged']=all(digest(Path(p).read_bytes())==h for p,h in original.items())
            r['clean_shutdown']=True;r['complete']=True;r.update(classify(r))
    except Exception:r['error']=traceback.format_exc();r['verdict']='SETUP_OR_INCOMPLETE'
    finally:
        if f:f.finish()
        (args.out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({'verdict':r['verdict'],'proven_attempts':r.get('proven_attempts'),'error':r.get('error')}))
    if not r['complete']:raise SystemExit(2)
if __name__=='__main__':main()
