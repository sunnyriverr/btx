"""Fail-closed consumer; framework skip/error cannot become a passing upload."""
import json
C=8<<20
def validate(r,framework_returncode):
 assert framework_returncode==0
 assert r['status']=='PASS' and r['provider']=='MINIO' and r['fake'] is False
 assert r['source_bytes']==2*C and len(r['source_sha384'])==96
 assert r['before_restart'] is True and r['after_restart'] is True
 assert int(r['head']['content-length'])==2*C
 assert r['head']['etag'].strip('"').endswith('-2')
 assert len(r['part_heads'])==2 and [int(h['content-length']) for h in r['part_heads']]==[C,C]
 return True
if __name__=='__main__':
 import sys
 validate(json.load(open(sys.argv[1])),int(sys.argv[2]));print('REAL_MINIO_CONTROL_VERIFIED')
