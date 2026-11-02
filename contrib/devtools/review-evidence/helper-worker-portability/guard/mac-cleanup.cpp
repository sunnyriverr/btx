#include <util/subprocess.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <cerrno>
// Windows process shims reject fork, so no worker child reaches this there.
void CloseWorkerDescriptors()
{
#ifndef _WIN32
    subprocess::detail::subprocess_close_all_fds(/*except_fd=*/-1);
#endif
}


int main(){int p[2];if(pipe(p))return 2;int s=socket(AF_INET,SOCK_STREAM,0);if(s<3)return 3;
CloseWorkerDescriptors();for(int fd:{p[0],p[1],s}){errno=0;if(fcntl(fd,F_GETFD)!=-1 || errno!=EBADF)return 4;}
if(fcntl(0,F_GETFD)<0 || fcntl(1,F_GETFD)<0 || fcntl(2,F_GETFD)<0)return 5;return 0;}
