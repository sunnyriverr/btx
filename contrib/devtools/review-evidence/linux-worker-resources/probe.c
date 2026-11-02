#include <stdlib.h>
#include <stdio.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
int main(void) {
 const size_t bytes=(size_t)PROBE_MB*1024*1024;
 volatile unsigned char *p=malloc(bytes);
 if (!p) return 42;
 for(size_t i=0;i<bytes;i+=4096)p[i]=1;
 struct rusage usage;if(getrusage(RUSAGE_SELF,&usage))return 43;
 if((size_t)usage.ru_maxrss*1024<bytes*8/10)return 44;
 int fd=open("result.txt",O_WRONLY|O_CREAT|O_EXCL,0600);if(fd<0)return 45;
 const char output[]="native-memory-probe-ok\n";
 if(write(fd,output,sizeof(output)-1)!=sizeof(output)-1)return 46;
 close(fd);free((void*)p);return 0;
}
