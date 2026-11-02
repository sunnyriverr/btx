/* Finite owner-configured loader protocol fixture. No CUDA/inference, no sockets opened.
 * Observe existing descriptors without changing flags; exit after release or 45 seconds. */
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/un.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <string.h>
#include <errno.h>
int main(int argc,char **argv) {
 const char *record=getenv("BTX_TEST_RECORD"), *release=getenv("BTX_TEST_RELEASE");
 if (!record || !release) return 2;
 FILE *f=fopen(record,"w"); if(!f)return 3;
 fprintf(f,"{\"pid\":%d,\"ppid\":%d,\"args\":[\"--dir\",\"checkout\",\"%s\",\"%s\"],\"sockets\":[",getpid(),getppid(),"test", "control");
 int comma=0;
 for(int fd=3;fd<256;fd++) {
  struct sockaddr_storage ss; socklen_t len=sizeof(ss);int listen=-1; socklen_t olen=sizeof(listen);
  if(getsockname(fd,(struct sockaddr*)&ss,&len)!=0)continue;
  int sockopt_errno=0; if(getsockopt(fd,SOL_SOCKET,SO_ACCEPTCONN,&listen,&olen)!=0)sockopt_errno=errno;
  fprintf(f,"%s{\"fd\":%d,\"family\":%d,\"listening\":%d,\"sockopt_errno\":%d,\"inheritable\":%s,\"sockname\":",comma++?",":"",fd,ss.ss_family,listen,sockopt_errno,(fcntl(fd,F_GETFD)&FD_CLOEXEC)?"false":"true");
  if(ss.ss_family==AF_INET){char ip[INET_ADDRSTRLEN];struct sockaddr_in *v=(struct sockaddr_in*)&ss;inet_ntop(AF_INET,&v->sin_addr,ip,sizeof(ip));fprintf(f,"[\"%s\",%d]",ip,ntohs(v->sin_port));}
  else fprintf(f,"\"non-INET\"");
  fprintf(f,"}");
 }
 fprintf(f,"]}\n");fclose(f);
 const char *mode=getenv("BTX_TEST_MODE"); if(!mode)return 4;
 usleep(1000000);
 if(strcmp(mode,"infer")==0)puts("infer-ok");
 else if(strcmp(mode,"generate")==0){char input[4096];if(!fgets(input,sizeof(input),stdin)||!strstr(input,"hello-btx"))return 9;puts("{\"ok\":true,\"generated\":true,\"text\":\"echo:hello-btx\",\"backend\":\"synthetic\"}");}
 else if(strcmp(mode,"llama")==0){int found=0;for(int i=1;i+1<argc;i++)if(strcmp(argv[i],"-p")==0 && strcmp(argv[i+1],"hello-btx")==0)found=1;if(!found)return 10;puts("llama:hello-btx");}
 else return 37;
 return 0;
}
