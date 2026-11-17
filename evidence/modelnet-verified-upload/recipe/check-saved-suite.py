"""Validate the saved native-suite report and six rejection controls. No BTX run."""
import copy,gzip,hashlib,json,sys,xml.etree.ElementTree as ET
from pathlib import Path
from read_suite import validate
root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'suite-validation.json').read_text())
raw=gzip.decompress((root/'raw/cloud-suite.xml.gz').read_bytes())
assert hashlib.sha256(raw).hexdigest()==manifest['raw_sha256']
text=raw.decode().replace('\r\n','\n').replace('\r','\n')
result,normalized=validate(text,0)
assert hashlib.sha256(normalized.encode()).hexdigest()==manifest['normalized_sha256']
tree=ET.fromstring(normalized)
for name,edit in [('failure',lambda t:(t.set('failures','1'),ET.SubElement(next(c for c in t.iter('testcase')if c.attrib.get('classname')=='modelnet_cloud_tests'),'failure'))),('selectedskip',lambda t:ET.SubElement(next(c for c in t.iter('testcase')if c.attrib.get('classname')=='modelnet_cloud_tests'),'skipped')),('missingcase',lambda t:next(c for c in t.iter('testcase')if c.attrib.get('name')=='cloud_verified_reader_empty_identity').set('name','MISSING')),('wrongcount',lambda t:t.set('tests','999'))]:
 t=copy.deepcopy(tree);edit(t);rejected=False
 try:validate(ET.tostring(t,encoding='unicode'),0)
 except(AssertionError,ET.ParseError):rejected=True
 assert rejected,name
for name,value,code in [('nonzeroexit',text,1),('truncated',text[:len(text)//2],0)]:
 rejected=False
 try:validate(value,code)
 except(AssertionError,ET.ParseError):rejected=True
 assert rejected,name
print(json.dumps({'saved_suite':result,'negative_controls':6,'BTX_reruns':0}))
