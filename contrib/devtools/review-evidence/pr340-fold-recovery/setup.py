from pathlib import Path
import subprocess,json,hashlib,os,datetime
r=Path('/BTX_REVIEW_ROOT');out=r/'pr340-fold-rerun';out.mkdir(exist_ok=True);repo=r/'toolchain-2026-10-31/source';src=out/'source';build=out/'build';head='3c1e9b4ab4ea93ca642df079e238ac56179a9166'
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.STDOUT)
prior={'head':git('rev-parse','HEAD').decode().strip(),'status':git('status','--porcelain=v1').decode(),'protected':{f:hashlib.sha256((repo/f).read_bytes()).hexdigest() for f in ['src/net_processing.cpp','src/test/peerman_tests.cpp']}}
(out/'prior-state.json').write_text(json.dumps(prior,indent=2)+'\n')
assert git('rev-parse','70e35da0:test/functional')==git('rev-parse',head+':test/functional'),'Framework changed: inspect delta'
if not src.exists():
 git('worktree','add','--detach','--no-checkout',str(src),head)
 for args in [('sparse-checkout','init','--cone'),('sparse-checkout','set','cmake','contrib','depends','doc','scripts/ci','share','src','test/functional'),('checkout',head)]:subprocess.check_output(['git','-C',str(src),*args],stderr=subprocess.STDOUT)
patch=r/'pr340-pinned-metal/exact-regtest1124-fixture.patch'
subprocess.run(['git','-C',str(src),'apply','--check',str(patch)],check=True);subprocess.run(['git','-C',str(src),'apply',str(patch)],check=True)
assert subprocess.check_output(['git','-C',str(src),'diff','--name-only']).decode().splitlines()==['src/kernel/chainparams.cpp']
args=json.loads((r/'pr362-admission/configure-command.json').read_text());args[args.index('-S')+1]=str(src);args[args.index('-B')+1]=str(build);args=[a.replace('-DBTX_BUILD_RC_PROVER_PROTOTYPE=ON','-DBTX_BUILD_RC_PROVER_PROTOTYPE=OFF').replace('-DENABLE_WALLET=OFF','-DENABLE_WALLET=ON') for a in args]
(out/'configure-command.json').write_text(json.dumps(args,indent=2)+'\n')
with (out/'configure.log').open('wb') as f:p=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT)
print('configure',p.returncode);print((out/'configure.log').read_text()[-1000:])
