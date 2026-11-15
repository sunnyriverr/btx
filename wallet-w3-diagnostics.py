from pathlib import Path
import json,re,datetime
root=Path.cwd();private=root/'w3-private-runtime/private.log';out=root/'records';out.mkdir(exist_ok=True);result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'raw_log_uploaded':False,'wallet_files_uploaded':False}
if private.is_file():
 text=private.read_text(errors='replace');result['source_frames']=[{'file':p.replace(str(root),'WORKSPACE'),'line':int(line),'function':func} for p,line,func in re.findall(r'File "([^"\n]+)", line (\d+), in ([^\n]+)',text)][-20:];result['exception_classes']=re.findall(r'(?m)^([A-Za-z_]\w*(?:Error|Exception))(?=:|$)',text)[-5:]
receipt=root/'w3-public-receipt.json'
if receipt.is_file():(out/'w3-public-receipt.json').write_bytes(receipt.read_bytes())
else:result['receipt_missing']=True
(out/'sanitized-diagnostics.json').write_text(json.dumps(result,indent=2)+'\n')
