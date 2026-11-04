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
 if (!record || !release || argc!=5) return 2;
 FILE *f=fopen(record,"w"); if(!f)return 3;
 fprintf(f,"{\"pid\":%d,\"ppid\":%d,\"args\":[\"--dir\",\"checkout\",\"%s\",\"%s\"],\"sockets\":[",getpid(),getppid(),argv[3],argv[4]);
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
 puts("{\"ok\":true,\"smoke_passed\":false,\"bytes_on_device\":0,\"device_name\":\"synthetic-protocol-fixture-no-GPU\"}");fflush(stdout);
 const time_t until=time(NULL)+45;
 while(access(release,F_OK)!=0 && time(NULL)<until)usleep(50000);
 char path[4096];snprintf(path,sizeof(path),"%.*s.exited",(int)(strlen(record)-5),record);
 f=fopen(path,"w");if(f){fputs("normal exit\n",f);fclose(f);}return 0;
}
