"""Validate saved Boost detailed output; no native execution or network."""
import re,collections

def validate(text,code,expected):
 s=re.sub(r'\x1b\[[0-9;]*m','',text)
 assert code==0,'suite process failure'
 assert expected and len(expected)==len(set(expected)),'invalid expected cases'
 for phrase in ('Entering test case','Leaving test case'):
  names=re.findall(re.escape(phrase)+r' "([^"\n]+)"',s)
  assert collections.Counter(names)==collections.Counter(expected),'missing/duplicate execution '+phrase
 passed=re.findall(r'^\s*Test case "modelnet_economy_tests/([^"\n]+)" has passed with:',s,re.M)
 assert collections.Counter(passed)==collections.Counter(expected),'missing/duplicate pass'
 assert not re.search(r'error: in "|fatal error:|uncaught exception|^\s*Test (?:case|suite|module) .*has failed',s,re.M),'reported failure'
 m=re.search(r'Test module "Bitcoin Core Test Suite" has passed with:\s*(\d+) test cases out of (\d+) passed\s*(\d+) assertions out of (\d+) passed',s)
 assert m and int(m[1])==int(m[2])==len(expected) and int(m[3])==int(m[4])>0,'module totals'
 n=re.search(r'Test suite "modelnet_economy_tests" has passed with:\s*(\d+) test cases out of (\d+) passed\s*(\d+) assertions out of (\d+) passed',s)
 assert n and m.groups()==n.groups(),'suite totals'
 return {'cases':int(m[1]),'assertions':int(m[3]),'exit':code,'report_format':'Boost detailed, not short No errors detected banner'}
