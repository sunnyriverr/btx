#include <atomic>
#include <chrono>
#include <algorithm>
#include <cerrno>
#include <cstdint>
#include <string>
#include <iostream>
using SOCKET=int;
#if SIMULATE_WINDOWS
#define WSAEINTR 10004
#define WSAEWOULDBLOCK 10035
#define WSAEAGAIN EAGAIN
#else
#define WSAEINTR EINTR
#define WSAEWOULDBLOCK EWOULDBLOCK
#define WSAEAGAIN EAGAIN
#endif
struct Case {const char* name; int first; int stale_errno; bool cancel; bool wait_timeout; bool expired; bool expected;};
static Case active; static int calls=0,waits=0,last_wsa_error=0;static std::atomic<bool>* token;
int WSAGetLastError(){return SIMULATE_WINDOWS?last_wsa_error:errno;}
int FakeWinsockSend(int,const char*,int n,int){
 ++calls; if(calls>1)return n;
 if(active.first==0)return n;
 if(active.first==1)return 1;
 if(active.first==2)return 0;
 int error=active.first==3?WSAEWOULDBLOCK:(active.first==4?WSAEINTR:(SIMULATE_WINDOWS?10054:ECONNRESET));
 last_wsa_error=error;if(!SIMULATE_WINDOWS)errno=error;
 if(active.cancel)token->store(true);
 return -1;
}
#define send FakeWinsockSend
inline int btx_send(SOCKET s,const void* buf,int len,int flags){return (send)(s,static_cast<const char*>(buf),len,flags);}
#undef send
#define send btx_send
bool WaitFd(int,bool,int,std::atomic<bool>* stop,std::string& err){
 ++waits;if(stop->load()){err="stopped";return false;}
 if(active.wait_timeout || waits>4){err="timeout";return false;}return true;
}
bool Run(std::string& err){
 int fd=3;std::atomic<bool> flag{false};auto* stop=&flag;token=stop;
 std::string wire="abc";size_t sent=0;
 const auto write_deadline=std::chrono::steady_clock::now()+std::chrono::milliseconds(active.expired?-1:100);
        while (sent < wire.size()) {
            const auto left = std::chrono::duration_cast<std::chrono::milliseconds>(
                write_deadline - std::chrono::steady_clock::now()).count();
            if (left <= 0) {
                err = "unix write timeout";
                return false;
            }
            if (!WaitFd(fd, true, static_cast<int>(left), stop, err)) return false;
            const ssize_t n = ::send(fd, wire.data() + sent, wire.size() - sent, 0);
            const int send_error{n < 0 ? WSAGetLastError() : 0};
            if (n > 0) sent += static_cast<size_t>(n);
            else if (n < 0 && (send_error == WSAEINTR || send_error == WSAEAGAIN ||
                               send_error == WSAEWOULDBLOCK)) continue;
            else {
                err = "unix write";
                return false;
            }
        }
return sent==wire.size();}
int main(){int fails=0;for(Case c:{
 Case{"normal",0,0,false,false,false,true},
 Case{"partial",1,0,false,false,false,true},
 Case{"would_block",3,0,false,false,false,true},
 Case{"interrupted",4,0,false,false,false,true},
 Case{"fatal_with_stale_retry_errno",5,EAGAIN,false,false,false,false},
 Case{"zero_write",2,0,false,false,false,false},
 Case{"cancel_on_retry",3,0,true,false,false,false},
 Case{"wait_timeout",0,0,false,true,false,false},
 Case{"expired_deadline",0,0,false,false,true,false}}){
 active=c;calls=waits=last_wsa_error=0;errno=c.stale_errno;std::string err;bool got=Run(err);bool pass=got==c.expected;
 if(c.cancel)pass=pass&&err=="stopped";
 if(c.wait_timeout)pass=pass&&err=="timeout";
 if(c.expired)pass=pass&&err=="unix write timeout";
 if(c.first==5)pass=pass&&calls==1;
 std::cout<<c.name<<" "<<(pass?"PASS":"FAIL")<<" calls="<<calls<<" err="<<err<<"\n";fails+=!pass;
 }return fails?1:0;}
