"""Offline classifier and mutation ordering checks; does not start BTX or HTTP."""
import ast,io,json
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from check import classify
from origin import Origin
from run import UpdatingOrigin,CHUNK,OFFSET,TOTAL

r=Path(__file__).resolve().parent
for p in r.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
base={'finished':True,'clean_shutdown':True,'first_part_seen':True,'changed':False,'catalog_sha384':'a','original_sha384':'a','changed_sha384':'b','cloud_success':True,'remote_sha384':'a'}
cases=[('control',{},'CONTROL_PASS'),('different',{'changed':True,'mutation_before_first_part_reply':True,'remote_sha384':'b'},'CLOUD_SUCCESS_WITH_DIFFERENT_BYTES'),('preserved',{'changed':True,'mutation_before_first_part_reply':True},'VERIFIED_BYTES_PRESERVED'),('refused',{'changed':True,'mutation_before_first_part_reply':True,'cloud_success':False},'SOURCE_CHANGE_REPORTED_FAILURE'),('incomplete',{'finished':False},None),('failed_control',{'cloud_success':False},None),('wrong_import',{'catalog_sha384':'b'},None),('missing_path',{'changed':True},None),('missing_multipart',{'first_part_seen':False},None),('unexpected_bytes',{'remote_sha384':'c'},None),('shutdown',{'clean_shutdown':False},None)]
rows=[]
for name,delta,want in cases:
 try:got=classify({**base,**delta})
 except ValueError:got=None
 assert got==want,(name,got,want);rows.append({'name':name,'expected':want,'observed':got})
class MemoryFile(io.BytesIO):
 def __exit__(self,*_):return False
 def fileno(self):return 123
class Source:
 def __init__(self):self.file=MemoryFile(b'A'*TOTAL)
 def open(self,mode):assert mode=='r+b';return self.file
 def stat(self):return SimpleNamespace(st_size=len(self.file.getbuffer()))
for change in (False,True):
 source=Source();origin=UpdatingOrigin(source,change)
 # Supply only the inherited dispatch result. No listener, endpoint or product.
 with patch.object(Origin,'_handler') as parent,patch('run.os.fsync'):
  class Base:
   def _dispatch(self,path,query,body):
    assert source.file.getbuffer()[OFFSET:OFFSET+4096]==b'A'*4096
    return 200,b'',None,'multipart-part'
  parent.return_value=Base;handler=origin._handler().__new__(origin._handler())
  answer=handler._dispatch('/test',{'partNumber':['1']},b'A'*CHUNK)
  assert answer[0]==200 and origin.first_part_seen
  assert origin.changed==change
  assert source.file.getbuffer()[OFFSET:OFFSET+4096]==(b'B' if change else b'A')*4096
 source.file.close()
out={'syntax_files':len(list(r.glob('*.py'))),'classifier_cases':rows,'mutation_order_controls':2,'native_runs':0,'http_requests':0}
(r/'offline-result.json').write_text(json.dumps(out,indent=2)+'\n')
print('PASS:11classifier cases;2in-memory mutation-order controls; no BTX or HTTP execution')
