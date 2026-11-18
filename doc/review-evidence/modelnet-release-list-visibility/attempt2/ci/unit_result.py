"""Strict classification of the four intended maintained-regression failures."""
import collections,re
CASE='release_lists_respect_local_hide_without_changing_campaigns'
EXPECTED=['getrecentreleases: model 0, hidden=1','getrecentreleases: model 2, hidden=1','getfundablemodels: model 0, hidden=1','getrecentlyunlockedmodels: model 2, hidden=1']
def baseline_failures(text,code):
 text=re.sub(r'\x1b\[[0-9;]*m','',text)
 assert code==201,'wrong baseline exit'
 assert 'fatal error:' not in text and 'uncaught exception' not in text,'setup exception'
 rows=re.findall(r'error: in "modelnet_economy_tests/'+CASE+r'": ([^\n]+)',text)
 assert collections.Counter(x.strip() for x in rows)==collections.Counter(EXPECTED),('unexpected baseline failure messages',rows)
 assert len(re.findall(r'error: in "',text))==4,'unrelated assertion failure'
 return rows
