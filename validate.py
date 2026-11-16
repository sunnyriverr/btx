import json,sys
from pathlib import Path
REQUIRED={'accepted-head','accepted-files','openssl','gcc','cmake','settings-configure','settings-globs','settings-plan','settings-registration','settings-targets','settings-resources'}
def validate(r):
 assert r.get('complete') is True and not r.get('error'),'pilot incomplete or error'
 assert all(r.get(x) is True for x in ('checkpoint_verified','source_verified','composition_verified','base_feed_restored')),'identity gate missing'
 assert r.get('product_compile_executed') is False and r.get('product_tests_executed') is False,'pilot scope missing'
 steps=r.get('commands',[]);assert REQUIRED <= {x['step']for x in steps},'required plan gate missing'
 assert all(x.get('exit')==0 for x in steps),'command failed'
 assert 0<r.get('planned_steps',0)<=3000,'unexpected plan size'
 return True
if __name__=='__main__':
 r=json.loads(Path(sys.argv[1]).read_text());validate(r);print('RESTORE_AND_PLAN_PASS; no product compile or tests')
