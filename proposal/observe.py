"""Read-only listing observation on disposable campaigns; no execution on import."""
import argparse,hashlib,json,signal,socket,struct,tempfile,time,shutil
from pathlib import Path
from helpers import Helper,digest,require
EXPECTED='28d7ecb6c611e5676d85de7a64038bc7d07cd0b6b2fb2606390d5e6405838ad2'
LABELS=('open_target','open_control','released_target','released_control')
VIEWS=('search','recent_local','fundable','unlocked')
def contains(obj,mid):
 if isinstance(obj,str):return obj==mid or obj=='btx://'+mid
 if isinstance(obj,list):return any(contains(x,mid) for x in obj)
 if isinstance(obj,dict):return any(contains(v,mid) for v in obj.values())
 return False

def eligible(view):
 return LABELS[:2] if view=='fundable' else LABELS[2:] if view=='unlocked' else LABELS

def validate(r):
 require(r.get('complete') is True and r.get('binary_verified') is True,'incomplete or unverified')
 require(r.get('secret_disclosed') is True,'unlock prerequisite absent')
 require(len(set(r.get('models',{}).values()))==4,'distinct models absent')
 phases=r['phases']
 for phase in ('before','unhidden'):
  for view in VIEWS:
   for label in eligible(view):require(phases[phase][view].get(label) is True,'visible control missing '+phase+view+label)
 for phase in ('hidden','hidden_restart'):
  for view in VIEWS:
   for label in eligible(view):
    require(isinstance(phases[phase][view].get(label),bool),'membership not measured')
    if label.endswith('control'):require(phases[phase][view][label] is True,'unrelated entry vanished')
  for label in ('open_target','released_target'):require(phases[phase]['search'][label] is False,'search hide control failed')
 require(r.get('direct_lookup_preserved') is True,'by-ID access changed')
 require(r.get('campaign_state_preserved') is True,'campaign state changed')
 require(r.get('hide_acknowledged') is True and r.get('unhide_acknowledged') is True,'policy request failed')
 require(r.get('process_exits')==[0,0] and r.get('clean_cleanup') is True and r.get('runtime_removed') is True,'cleanup failed')
 found=[]
 for phase in ('hidden','hidden_restart'):
  for view in VIEWS[1:]:
   for label in eligible(view):
    if label.endswith('target') and phases[phase][view][label]:found.append({'phase':phase,'view':view,'model':label})
 require(r.get('violations')==found,'incorrect result classification')
 require(r.get('verdict')==('REPRODUCED_LISTING_INCONSISTENCY' if found else 'NOT_REPRODUCED'),'incorrect verdict')
 return True

def run(binary,out,expected=EXPECTED):
 out.mkdir(parents=True,exist_ok=False);root=Path(tempfile.mkdtemp(prefix='s2vis-'));h=None;exits=[];r={'complete':False,'binary_verified':digest(binary)==expected,'models':{},'phases':{}};start=time.monotonic()
 def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 def alarm(*_):raise TimeoutError('480second observation bound')
 signal.signal(signal.SIGALRM,alarm);signal.alarm(480)
 try:
  require(r['binary_verified'],'wrong binary')
  with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
  home=root/'helper';home.mkdir();h=Helper(binary,home,out,'local',64<<20,hostport=port);h.start();r['launch_args']=h.launch_args
  releases={};uris={}
  for i,label in enumerate(LABELS):
   model=root/(label+'.safetensors');header=json.dumps({'__metadata__':{'fixture':label}},separators=(',',':')).encode();model.write_bytes(struct.pack('<Q',len(header))+header)
   hosted=h.ok('hostmodel',[str(model)]);mid=hosted['model_id'];uri=hosted['uri'];r['models'][label]=mid;uris[label]=uri
   secret=('%02x'%(i+1))*32
   rel=h.ok('createmodelrelease',[{'uri':uri,'secret32_hex':secret,'refund_height':100000,'target_atoms':5000000,'display_name':label}]);releases[label]=rel['release_id']
   if label.startswith('released'):
    claim=h.ok('claimmodelrelease',[rel['release_id'],secret]);require(claim.get('secret_disclosed') is True,'supported unlock did not disclose secret')
  r['secret_disclosed']=True;r['releases']=releases
  def direct():
   return {label:h.ok('getmodelrelease',[rid]) for label,rid in releases.items()}
  def membership():
   requests={'search':('searchmodels',{'scope':'LOCAL','limit':100}),'recent_local':('getrecentreleases',{'scope':'LOCAL','limit':100}),'fundable':('getfundablemodels',{'limit':100}),'unlocked':('getrecentlyunlockedmodels',{'limit':100})};observed={}
   for view,(method,query) in requests.items():
    reply=h.ok(method,[query]);require(isinstance(reply.get('results'),list),'missing results array '+view)
    observed[view]={label:contains(reply['results'],mid) for label,mid in r['models'].items()}
   return observed
  original=direct();campaign_file=h.store/'campaigns.json';require(campaign_file.is_file(),'campaign file absent');original_campaigns=json.loads(campaign_file.read_text());r['phases']['before']=membership();save()
  for label in ('open_target','released_target'):require(h.ok('hidesearchmodel',[uris[label]]).get('hidden') is True,'hide refused')
  r['hide_acknowledged']=True;r['phases']['hidden']=membership();hidden_direct=direct()
  proc=h.proc;h.stop();exits.append(proc.returncode);h.start();r['phases']['hidden_restart']=membership();restart_direct=direct()
  for label in ('open_target','released_target'):require(h.ok('unhidesearchmodel',[uris[label]]).get('hidden') is False,'unhide refused')
  r['unhide_acknowledged']=True;r['phases']['unhidden']=membership();unhidden_direct=direct()
  r['direct_lookup_preserved']=all(contains(d[label],mid) for d in (original,hidden_direct,restart_direct,unhidden_direct) for label,mid in r['models'].items())
  r['campaign_state_preserved']=json.loads(campaign_file.read_text())==original_campaigns
  r['campaign_file_before']=original_campaigns;r['campaign_file_after']=json.loads(campaign_file.read_text())
  r['direct_responses']={'before':original,'hidden':hidden_direct,'restart':restart_direct,'unhidden':unhidden_direct}
  r['violations']=[{'phase':phase,'view':view,'model':label} for phase in ('hidden','hidden_restart') for view in VIEWS[1:] for label in eligible(view) if label.endswith('target') and r['phases'][phase][view][label]]
  r['verdict']='REPRODUCED_LISTING_INCONSISTENCY' if r['violations'] else 'NOT_REPRODUCED';r['complete']=True
 except Exception as e:r['error']=repr(e)
 finally:
  signal.alarm(0)
  if h:
   proc=h.proc;h.cleanup();exits.append(proc.poll() if proc else None);r['process_exits']=exits;r['clean_cleanup']=not h.cleanup_error and not h.forced and exits==[0,0]
  if h is None or h.proc is None or h.proc.poll() is not None:shutil.rmtree(root);r['runtime_removed']=True
  r['seconds']=time.monotonic()-start;save()
 validate(r)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--helper',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--sha256',default=EXPECTED);a=p.parse_args();run(a.helper.resolve(),a.out.resolve(),a.sha256)
