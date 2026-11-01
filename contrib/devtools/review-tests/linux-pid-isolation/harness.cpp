#include <modelnet/swarm_fsjail.h>
#include <signal.h>
#include <sys/wait.h>
#include <unistd.h>
#include <fstream>
#include <iostream>
#include <thread>
#include <chrono>
#include <filesystem>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sstream>
#include <vector>
void caught(int){_exit(42);}
int main(int argc,char**argv){
 if(argc!=3)return 2;
 int mode=std::stoi(argv[2]);
 int listener=socket(AF_INET,SOCK_STREAM,0);int yes=1;setsockopt(listener,SOL_SOCKET,SO_REUSEADDR,&yes,sizeof(yes));sockaddr_in addr{};addr.sin_family=AF_INET;addr.sin_addr.s_addr=htonl(INADDR_LOOPBACK);addr.sin_port=htons(45678);if(bind(listener,reinterpret_cast<sockaddr*>(&addr),sizeof(addr))||listen(listener,1))return 6;
 {std::ofstream marker("/tmp/btx-isolation/outside-marker");marker<<"outside";}
 fs::path root{argv[1]};fs::create_directories(root);
 int ready[2];if(pipe(ready))return 3;
 pid_t sentinel=fork();
 if(sentinel==0){close(ready[0]);signal(SIGUSR1,caught);char c='r';write(ready[1],&c,1);close(ready[1]);for(;;)pause();}
 if(sentinel<0)return 4;
 close(ready[1]);char c; if(read(ready[0],&c,1)!=1)return 5;close(ready[0]);
 {std::ofstream f(root/"target");f<<sentinel<<" "<<mode<<"\n";}
 fs::copy_file(fs::path("/tmp/btx-isolation/probe"),root/"probe",fs::copy_options::overwrite_existing);
 if(mode==9){std::ofstream broken(root/"probe",std::ios::trunc);broken<<"not an executable";}
 modelnet::SwarmFilesystemJailRequest q;q.helper=root/"probe";q.root=root;q.network_denied=true;q.max_wall_seconds=mode==7?1:3;q.max_tree_bytes=16*1024*1024;
 std::string err; auto result=modelnet::SwarmRunFilesystemJail(q,err);
 int st=0;pid_t seen=0;
 for(int i=0;i<30;i++){seen=waitpid(sentinel,&st,WNOHANG);if(seen==sentinel)break;std::this_thread::sleep_for(std::chrono::milliseconds(10));}
 bool delivered=seen==sentinel&&WIFEXITED(st)&&WEXITSTATUS(st)==42;
 if(seen==0){kill(sentinel,SIGTERM);waitpid(sentinel,&st,0);}
 std::ifstream file(root/"result");std::string line;std::getline(file,line);
 auto heartbeat=[&]{std::ifstream h(root/"heartbeat");std::string value;std::getline(h,value);return value;};
 std::string hb_before=heartbeat();
 bool clean=true;int leftovers=0;
 std::this_thread::sleep_for(std::chrono::milliseconds(100));
 for(const auto& entry:std::filesystem::directory_iterator("/proc")){
  std::error_code ec;auto exe=std::filesystem::read_symlink(entry.path()/"exe",ec);
  if(!ec&&exe==root/"probe") {clean=false;++leftovers;int owned=std::stoi(entry.path().filename().string());kill(owned,SIGKILL);}
 }
 std::string hb_after=heartbeat();
 bool heartbeat_stopped=hb_before==hb_after;
 clean=clean&&heartbeat_stopped;
 if(!heartbeat_stopped)std::this_thread::sleep_for(std::chrono::seconds(7));
 close(listener);
 bool run_ok=(mode==5||mode==9)?(!result.launched&&result.code=="JAIL_ABSENT"):
             mode==7?(!result.launched&&result.code=="JAIL_TIMEOUT"):
             (result.launched&&result.jailed&&result.child_status==(mode==4?(37<<8):0));
 bool safe=run_ok&&(mode==9||!line.empty())&&!delivered&&clean;
 std::cout<<"host_uid="<<getuid()<<" sentinel="<<sentinel<<" mode="<<mode<<" launched="<<result.launched<<" jailed="<<result.jailed<<" code="<<result.code<<" status="<<result.child_status<<" signal_delivered="<<delivered<<" heartbeat_stopped="<<heartbeat_stopped<<" clean="<<clean<<" leftovers="<<leftovers<<" safety_pass="<<safe<<" worker=["<<line<<"] err="<<err<<"\n";
 return safe?0:1;
}
