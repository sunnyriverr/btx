import socket,json,errno
def rpc_helper(path,method,params=[]):
 with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
  s.settimeout(20);s.connect(str(path));s.sendall((json.dumps({'id':1,'method':method,'params':params})+'\n').encode())
  try:s.shutdown(socket.SHUT_WR)
  except OSError as e:
   if e.errno!=errno.ENOTCONN:raise
  data=b''
  while b'\n' not in data:
   part=s.recv(65536)
   if not part:break
   data+=part
  d=json.loads(data)
  if d.get('error'):raise RuntimeError(d['error'])
  return d['result']
