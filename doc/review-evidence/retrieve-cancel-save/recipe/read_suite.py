"""Validate saved Boost JUnit, preserving failures and filtered-case distinctions.
Boost's all-level logger can embed an assertion containing ]]> inside its
system-out CDATA. Normalize only that text framing; preserve the raw evidence.
"""
import hashlib,json,re,xml.etree.ElementTree as ET
from pathlib import Path
REQUIRED={'cloud_verified_upload_ignores_external_source_changes','cloud_verified_reader_withholds_invalid_last_piece_and_retries','cloud_verified_reader_exact_lengths_and_corrupt_piece','cloud_verified_reader_empty_identity'}
def normalize(raw):
 changes=0
 def quote(m):
  nonlocal changes
  content=m.group(2);changes+=content.count(']]>')
  return '<'+m.group(1)+'><![CDATA['+content.replace(']]>',']]]]><![CDATA[>')+']]></'+m.group(1)+'>'
 return re.sub(r'<(system-out|system-err)><!\[CDATA\[(.*?)\]\]></\1>',quote,raw,flags=re.S),changes

def validate(raw,exit_code):
 assert exit_code==0,'native suite failed'
 normalized,changes=normalize(raw);root=ET.fromstring(normalized)
 assert root.tag=='testsuite' and int(root.attrib['errors'])==0 and int(root.attrib['failures'])==0,'suite errors'
 cases=list(root.iter('testcase'));active=[c for c in cases if c.find('skipped')is None];skipped=[c for c in cases if c.find('skipped')is not None]
 assert len(active)==int(root.attrib['tests']) and len(skipped)==int(root.attrib['skipped']),'case count mismatch'
 assert active and all(c.attrib.get('classname')=='modelnet_cloud_tests'for c in active),'wrong executed suite'
 selected=[c for c in cases if c.attrib.get('classname')=='modelnet_cloud_tests']
 assert len(active)==len(selected) and not any(c.find('skipped')is not None for c in selected),'selected cloud case skipped'
 assert not list(root.iter('failure')) and not list(root.iter('error')),'case failure'
 names={c.attrib['name']for c in selected};assert REQUIRED<=names,'required regression missing'
 return {'cloud_cases':len(selected),'filtered_noncloud_cases':len(skipped),'cdata_framing_repairs':changes,'required':sorted(REQUIRED),'native_exit':exit_code},normalized
if __name__=='__main__':
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('xml',type=Path);ap.add_argument('--exit-code',type=int,required=True);a=ap.parse_args();receipt,normalized=validate(a.xml.read_text(),a.exit_code);a.xml.with_suffix('.normalized.xml').write_text(normalized);print(json.dumps(receipt))
