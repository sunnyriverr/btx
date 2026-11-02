import socket,subprocess,json,struct
rows=json.loads(subprocess.check_output(['ip','-j','addr'],text=True));iface=next(x for x in rows if x['ifname']=='eth0');ip=next(x['local'] for x in iface['addr_info'] if x['family']=='inet');index=iface['ifindex'];result={'selected_interface':iface['ifname'],'selected_index':index,'cases':{}}
for kind in ['off_scope','multicast']:
 with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as r,socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
  r.bind(('0.0.0.0',0));port=r.getsockname()[1];r.setsockopt(socket.IPPROTO_IP,8,1);r.settimeout(3)
  r.setsockopt(socket.IPPROTO_IP,socket.IP_ADD_MEMBERSHIP,socket.inet_aton('239.192.0.35')+socket.inet_aton(ip))
  s.bind((ip,0));s.setsockopt(socket.IPPROTO_IP,socket.IP_MULTICAST_IF,socket.inet_aton(ip));s.setsockopt(socket.IPPROTO_IP,socket.IP_MULTICAST_TTL,0);s.setsockopt(socket.IPPROTO_IP,socket.IP_MULTICAST_LOOP,1)
  destination='127.0.0.1' if kind=='off_scope' else '239.192.0.35';s.sendto(kind.encode(),(destination,port));data,cmsgs,flags,source=r.recvmsg(128,128)
  assert data==kind.encode() and source[0]==ip and not flags&(socket.MSG_TRUNC|socket.MSG_CTRUNC)
  pkt=next(c[2] for c in cmsgs if c[:2]==(socket.IPPROTO_IP,8));idx=struct.unpack_from('I',pkt)[0];dest=socket.inet_ntoa(pkt[8:12]);assert idx==(1 if kind=='off_scope' else index);assert dest==destination
  result['cases'][kind]={'incoming_index':idx,'incoming_interface':socket.if_indextoname(idx),'destination':dest,'source_is_own_private_ip':True,'kernel_IP_PKTINFO':True}
print(json.dumps(result,indent=2))
