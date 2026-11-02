#!/usr/bin/env python3
"""Second-process driver; run only against an already-open isolated Atlas test app.
This does not automate or replace native UI observations. Keep its connected
backend disposable, loopback-only, wallet-disabled and without model peers.
"""
import argparse,hashlib,json,pathlib,subprocess,tempfile,time
p=argparse.ArgumentParser();p.add_argument('binary',type=pathlib.Path);p.add_argument('case',choices=['mixed','file','uri','recovery','none']);p.add_argument('--expected-sha256',required=True);a=p.parse_args()
assert hashlib.sha256(a.binary.read_bytes()).hexdigest()==a.expected_sha256,'binary mismatch'
with tempfile.TemporaryDirectory(prefix='atlas-preview-case-') as tmp:
 f=pathlib.Path(tmp)/'request.btx'
 value='btx:atlas-test-mixed-file?amount=0.6' if a.case=='mixed' else 'btx:atlas-test-'+a.case+'?amount=0.3'
 f.write_text(value)
 args={'mixed':['btx:atlas-test-direct?amount=0.2',str(f)],'file':[str(f)],'uri':['btx:atlas-test-uri-control?amount=0.4'],'recovery':[str(f)],'none':[]}[a.case]
 start=time.monotonic();r=subprocess.run([str(a.binary.resolve()),*args],capture_output=True,text=True,timeout=15)
 print(json.dumps({'argv':args,'returncode':r.returncode,'seconds':time.monotonic()-start,'stdout':r.stdout,'stderr':r.stderr,'file_contents':value},indent=2))
 # Keep the actual file alive until the first instance has read it.
 input('Observe normal UI polling; close previews without parsing, record values and footer times; press Enter after this case is finished: ')
