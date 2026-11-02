#!/usr/bin/env python3
"""Portable adaptation of the captured launcher; not an additional executed test.
Launch only against the already-running SAME isolated binary, normally connected
to a disposable wallet-disabled loopback node. Observe native UI, do not parse.
"""
import argparse,hashlib,json,pathlib,subprocess,tempfile,time,os
p=argparse.ArgumentParser();p.add_argument('binary',type=pathlib.Path);p.add_argument('case',choices=['sole','mixed','file','none']);p.add_argument('--expected-sha256',required=True);p.add_argument('--first-pid',required=True,type=int);a=p.parse_args()
assert hashlib.sha256(a.binary.read_bytes()).hexdigest()==a.expected_sha256
os.kill(a.first_pid,0)
with tempfile.TemporaryDirectory(prefix='atlas-guard-case-') as tmp:
 f=pathlib.Path(tmp)/'request.btx'
 f.write_text('btx:atlas-guard-mixed-file?amount=0.4' if a.case=='mixed' else 'btx:atlas-guard-file?amount=0.3')
 args={'sole':['btx:atlas-guard-sole?amount=0.125'],'mixed':['btx:atlas-guard-mixed?amount=0.2',str(f)],'file':[str(f)],'none':[]}[a.case]
 start=time.monotonic();r=subprocess.run([str(a.binary.resolve()),*args],capture_output=True,text=True,timeout=15)
 os.kill(a.first_pid,0)
 print(json.dumps({'argv':args,'exit':r.returncode,'elapsed':time.monotonic()-start,'stdout':r.stdout,'stderr':r.stderr,'fixture':f.read_text()},indent=2))
 assert r.returncode==0
 input('Observe ordinary native UI refreshes, close previews without parsing, record values/footer times; Enter only after observation is complete: ')
