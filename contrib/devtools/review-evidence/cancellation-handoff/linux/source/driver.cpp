#include <modelnet/supervisor.h>
#include <modelnet/helper.h>
#include <iostream>
#include <csignal>
int main(int argc,char** argv){
 signal(SIGPIPE,SIG_IGN);
 if(argc<4)return 2;
 if(std::string(argv[1])=="call"){
  UniValue p(UniValue::VARR),result;p.push_back(argv[3]);std::string err;
  bool ok=modelnet::CallUnixRpc(fs::PathFromString(argv[2]),"getmodel",p,result,err);
  UniValue o(UniValue::VOBJ);o.pushKV("ok",ok);o.pushKV("error",err);o.pushKV("result",result);std::cout<<o.write()<<std::endl;return ok?0:1;
 }
 modelnet::HelperLaunchConfig c;c.modeldir=fs::PathFromString(argv[1]);c.rpc_socket=c.modeldir/"rpc.sock";c.helper_exe=fs::PathFromString(argv[2]);c.external_socket=std::string(argv[3])=="external";
 c.storage_arg="0";c.seed="none";c.bind="0";c.follow_peers=false;c.lan_discovery=false;
 modelnet::HelperSupervisor s(c);std::string err;bool started=s.Start(err);std::cout<<"START "<<started<<" "<<err<<std::endl;
 std::string command;while(std::getline(std::cin,command)){
  if(command=="status"){auto st=s.Snapshot();std::cout<<"STATUS "<<modelnet::HelperStateName(st.state)<<" "<<st.managed_by_btxd<<" "<<st.pid<<std::endl;}
  if(command=="stop"){s.Stop();std::cout<<"STOPPED"<<std::endl;break;}
 }
}
