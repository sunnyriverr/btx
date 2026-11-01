#include <cerrno>
#include <cstdio>
#include <csignal>
#include <unistd.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <sys/wait.h>
#include <cstdlib>
void child_signal(int){_exit(19);}
int main(){
 FILE* in=fopen("/target","r");int target=0, mode=0;
 if(!in||fscanf(in,"%d %d",&target,&mode)!=2||target<=1)return 10;
 fclose(in);
 errno=0;int rc=mode==1?kill(target,SIGUSR1):mode==2?kill(2147483647,SIGUSR1):0;int e=errno;
 int fd=open("/tmp/btx-isolation/outside-marker",O_RDONLY);bool outside=fd>=0;if(fd>=0)close(fd);
 int sock=socket(AF_INET,SOCK_STREAM,0);sockaddr_in addr{};addr.sin_family=AF_INET;addr.sin_addr.s_addr=htonl(INADDR_LOOPBACK);addr.sin_port=htons(45678);int net=connect(sock,reinterpret_cast<sockaddr*>(&addr),sizeof(addr));if(sock>=0)close(sock);
 FILE* out=fopen("/result","w");if(!out)return 11;
 fprintf(out,"uid=%d gid=%d pid=%d ppid=%d mode=%d target=%d rc=%d errno=%d outside_open=%d host_loopback_connect=%d\n",getuid(),getgid(),getpid(),getppid(),mode,target,rc,e,outside,net);
 fclose(out);
 if(mode==3){pid_t c=fork();if(c<0)return 20;if(c==0)_exit(17);int st;if(waitpid(c,&st,0)!=c||!WIFEXITED(st)||WEXITSTATUS(st)!=17)return 21;}
 if(mode==8){int fds[2];if(pipe(fds))return 30;pid_t c=fork();if(c<0)return 31;
 if(c==0){close(fds[0]);signal(SIGUSR1,child_signal);char ok='r';if(write(fds[1],&ok,1)!=1)_exit(32);close(fds[1]);for(;;)pause();}
 close(fds[1]);char ok;if(read(fds[0],&ok,1)!=1)return 33;close(fds[0]);if(kill(c,SIGUSR1))return 34;int st;if(waitpid(c,&st,0)!=c||!WIFEXITED(st)||WEXITSTATUS(st)!=19)return 35;}
 if(mode==4)return 37;
 if(mode==5){kill(getpid(),SIGTERM);return 23;}
 if(mode==6||mode==7){
  pid_t c=fork();if(c<0)return 24;
  if(c==0){if(setsid()<0)_exit(25);for(int i=0;i<600;i++){FILE* h=fopen("/heartbeat","w");if(h){fprintf(h,"%d",i);fclose(h);}usleep(10000);}_exit(0);}
  for(int i=0;i<100&&access("/heartbeat",F_OK)!=0;i++)usleep(10000);
  if(access("/heartbeat",F_OK)!=0)return 26;
  if(mode==7)for(;;)pause();
 }
 return outside||net==0?12:0;
}
