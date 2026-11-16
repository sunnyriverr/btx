#define _GNU_SOURCE
#include <dlfcn.h>
#include <signal.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/syscall.h>
static void boundary(const char *p) {
 const char *arm=getenv("BTX737_ARM");
 if (!arm || !p || !strstr(p,"/file_stream_jobs/") || strlen(p)<5 || strcmp(p+strlen(p)-5,".json")) return;
 if (access(arm,F_OK)) return;
 const char *mark=getenv("BTX737_BOUNDARY");
 int f=syscall(SYS_openat,AT_FDCWD,mark,O_WRONLY|O_CREAT|O_TRUNC,0600);
 if(f>=0){syscall(SYS_write,f,p,strlen(p));syscall(SYS_close,f);}
 raise(SIGSTOP);
}
int unlink(const char*p){boundary(p);return ((int(*)(const char*))dlsym(RTLD_NEXT,"unlink"))(p);}
int unlinkat(int d,const char*p,int f){boundary(p);return ((int(*)(int,const char*,int))dlsym(RTLD_NEXT,"unlinkat"))(d,p,f);}
int remove(const char*p){boundary(p);return ((int(*)(const char*))dlsym(RTLD_NEXT,"remove"))(p);}
