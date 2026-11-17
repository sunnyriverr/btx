"""Check modified origin hook paths without BTX or HTTP; do not count as native evidence."""
import ast,io,json
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from origin import Origin
from native import UploadOrigin,CHUNK,TOTAL,OFFSET,payload
r=Path(__file__).resolve().parent
for p in r.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
class MemoryFile(io.BytesIO):
 def __exit__(self,*_):return False
 def fileno(self):return 123
class Source:
 def __init__(self):self.file=MemoryFile(payload())
 def open(self,mode):assert mode=='r+b';return self.file
 def stat(self):return SimpleNamespace(st_size=len(self.file.getbuffer()))
checks=[]
for layout in ('SOURCE_FILES','PIECE_OBJECTS'):
 for change in (False,True):
  src=Source();owner=UploadOrigin(src,layout,change)
  with patch.object(Origin,'_handler') as factory,patch('native.os.fsync'):
   class Base:
    def _dispatch(self,path,q,body):
     assert src.file.getbuffer()[OFFSET:OFFSET+4096]==b'A'*4096
     return 200,b'',None,'multipart-part' if layout=='SOURCE_FILES' else 'ordinary-put'
   factory.return_value=Base;kind=owner._handler();handler=kind.__new__(kind);handler.command='PUT'
   q={'partNumber':['1']} if layout=='SOURCE_FILES' else {};path='/key' if layout=='SOURCE_FILES' else '/artifacts/a/0/0.piece'
   response=handler._dispatch(path,q,b'A'*(CHUNK if layout=='SOURCE_FILES' else 4<<20));assert response[0]==200 and owner.boundary_seen and owner.changed==change
   assert src.file.getbuffer()[OFFSET:OFFSET+4096]==(b'B' if change else b'A')*4096
   owner.fail_part2=True;assert handler._dispatch('/key',{'partNumber':['2']},b'x')[0]==500
  src.file.close();checks.append({'layout':layout,'change':change,'ordering_and_fault_control':True})
print(json.dumps({'syntax':True,'hook_cases':checks,'native_runs':0}))
