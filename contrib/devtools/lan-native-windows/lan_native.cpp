// Native Windows component qualification: legitimate packets, no model helper.
#include <modelnet/native_discovery.h>
#include <modelnet/model_nat.h>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <iphlpapi.h>
#include <array>
#include <chrono>
#include <cstring>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

struct Socket {
    SOCKET fd{INVALID_SOCKET};
    ~Socket() { if (fd != INVALID_SOCKET) closesocket(fd); }
};
std::string Interface()
{
    ULONG size = 16384;
    std::vector<unsigned char> data(size);
    auto* first = reinterpret_cast<IP_ADAPTER_ADDRESSES*>(data.data());
    ULONG code = GetAdaptersAddresses(AF_INET, GAA_FLAG_SKIP_ANYCAST | GAA_FLAG_SKIP_MULTICAST | GAA_FLAG_SKIP_DNS_SERVER, nullptr, first, &size);
    if (code == ERROR_BUFFER_OVERFLOW && size <= 1024*1024) {
        data.resize(size); first = reinterpret_cast<IP_ADAPTER_ADDRESSES*>(data.data());
        code = GetAdaptersAddresses(AF_INET, GAA_FLAG_SKIP_ANYCAST | GAA_FLAG_SKIP_MULTICAST | GAA_FLAG_SKIP_DNS_SERVER, nullptr, first, &size);
    }
    if (code != NO_ERROR) return {};
    for (auto* adapter=first; adapter; adapter=adapter->Next) {
        if (adapter->OperStatus!=IfOperStatusUp || adapter->IfType==IF_TYPE_SOFTWARE_LOOPBACK) continue;
        for (auto* address=adapter->FirstUnicastAddress; address; address=address->Next) {
            if (!address->Address.lpSockaddr || address->Address.lpSockaddr->sa_family!=AF_INET || address->OnLinkPrefixLength==0 || address->OnLinkPrefixLength>32) continue;
            auto* ipv4=reinterpret_cast<sockaddr_in*>(address->Address.lpSockaddr);
            char ip[INET_ADDRSTRLEN]{};
            if (inet_ntop(AF_INET,&ipv4->sin_addr,ip,sizeof(ip)) && modelnet::LanHintSourceAllowed(ip)) {
                std::cout << "INTERFACE ip=" << ip << " index=" << adapter->IfIndex << " prefix=" << unsigned(address->OnLinkPrefixLength) << '\n';
                return ip;
            }
        }
    }
    return {};
}
modelnet::LanBeacon Beacon(uint16_t port) {
    modelnet::LanBeacon value; value.network="regtest"; value.port=port; value.instance.fill(7); return value;
}
bool Discover(const std::string& ip, bool multicast)
{
    modelnet::NativeLanDiscovery discovery; std::string error;
    if (!discovery.Open("regtest",ip,30400,error)) {
        std::cout << "OPEN_FAILED multicast=" << multicast << " error=" << error << " wsa=" << WSAGetLastError() << '\n'; return false;
    }
    auto begin=std::chrono::steady_clock::now(); discovery.Tick();
    if (std::chrono::steady_clock::now()-begin>std::chrono::milliseconds(500)) {
        std::cout << "IDLE_TICK_SLOW\n"; return false;
    }
    Socket sender; sender.fd=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);
    if (sender.fd==INVALID_SOCKET) { std::cout<<"SENDER_SOCKET_FAILED wsa="<<WSAGetLastError()<<'\n'; return false; }
    sockaddr_in local{}; local.sin_family=AF_INET; inet_pton(AF_INET,ip.c_str(),&local.sin_addr);
    if (bind(sender.fd,reinterpret_cast<sockaddr*>(&local),sizeof(local))!=0) { std::cout<<"SENDER_BIND_FAILED wsa="<<WSAGetLastError()<<'\n';return false; }
    DWORD ttl=0, loop=1;
    if (setsockopt(sender.fd,IPPROTO_IP,IP_MULTICAST_IF,reinterpret_cast<const char*>(&local.sin_addr),sizeof(local.sin_addr)) ||
        setsockopt(sender.fd,IPPROTO_IP,IP_MULTICAST_TTL,reinterpret_cast<const char*>(&ttl),sizeof(ttl)) ||
        setsockopt(sender.fd,IPPROTO_IP,IP_MULTICAST_LOOP,reinterpret_cast<const char*>(&loop),sizeof(loop))) { std::cout<<"SENDER_OPTIONS_FAILED wsa="<<WSAGetLastError()<<'\n';return false; }
    const uint16_t port=multicast?30310:30311;
    std::array<unsigned char,modelnet::MODEL_LAN_BEACON_SIZE> wire{};
    if (!modelnet::EncodeLanBeacon(Beacon(port),wire)) return false;
    sockaddr_in target{}; target.sin_family=AF_INET; target.sin_port=htons(modelnet::MODEL_LAN_DISCOVERY_PORT);
    inet_pton(AF_INET,multicast?"239.192.0.35":ip.c_str(),&target.sin_addr);
    const int sent=sendto(sender.fd,reinterpret_cast<const char*>(wire.data()),static_cast<int>(wire.size()),0,reinterpret_cast<sockaddr*>(&target),sizeof(target));
    if (sent!=static_cast<int>(wire.size())) { std::cout<<"SEND_FAILED bytes="<<sent<<" wsa="<<WSAGetLastError()<<'\n';return false; }
    const std::string wanted=ip+":"+std::to_string(port);
    for (int i=0;i<300;++i) {
        discovery.Tick();
        for (const auto& endpoint:discovery.Endpoints()) if (endpoint==wanted) {
            std::cout << "HINT multicast=" << multicast << " endpoint=" << endpoint << '\n'; return true;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    std::cout << "HINT_NOT_OBSERVED multicast=" << multicast << " sent=" << sent << '\n'; return false;
}
// Diagnostic only after a discovery failure; never substitutes for a hint.
bool BasicUdp(const std::string& ip, bool multicast)
{
    Socket receive; receive.fd=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);
    Socket send; send.fd=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);
    if(receive.fd==INVALID_SOCKET||send.fd==INVALID_SOCKET)return false;
    DWORD timeout=1000,ttl=0,loop=1;
    if(setsockopt(receive.fd,SOL_SOCKET,SO_RCVTIMEO,reinterpret_cast<const char*>(&timeout),sizeof(timeout)))return false;
    sockaddr_in local{};local.sin_family=AF_INET;
    if(bind(receive.fd,reinterpret_cast<sockaddr*>(&local),sizeof(local)))return false;
    int length=sizeof(local);if(getsockname(receive.fd,reinterpret_cast<sockaddr*>(&local),&length))return false;
    in_addr iface{};inet_pton(AF_INET,ip.c_str(),&iface);
    if(multicast){
        ip_mreq membership{};inet_pton(AF_INET,"239.192.0.35",&membership.imr_multiaddr);membership.imr_interface=iface;
        if(setsockopt(receive.fd,IPPROTO_IP,IP_ADD_MEMBERSHIP,reinterpret_cast<const char*>(&membership),sizeof(membership)))return false;
    }
    if(setsockopt(send.fd,IPPROTO_IP,IP_MULTICAST_IF,reinterpret_cast<const char*>(&iface),sizeof(iface))||
       setsockopt(send.fd,IPPROTO_IP,IP_MULTICAST_TTL,reinterpret_cast<const char*>(&ttl),sizeof(ttl))||
       setsockopt(send.fd,IPPROTO_IP,IP_MULTICAST_LOOP,reinterpret_cast<const char*>(&loop),sizeof(loop)))return false;
    inet_pton(AF_INET,multicast?"239.192.0.35":ip.c_str(),&local.sin_addr);
    const char bytes[]="LAN400 local UDP control";
    if(sendto(send.fd,bytes,sizeof(bytes),0,reinterpret_cast<sockaddr*>(&local),sizeof(local))!=sizeof(bytes))return false;
    char buffer[64]{};const int got=recvfrom(receive.fd,buffer,sizeof(buffer),0,nullptr,nullptr);
    return got==sizeof(bytes)&&std::memcmp(buffer,bytes,sizeof(bytes))==0;
}
int main()
{
    WSADATA startup{}; if (WSAStartup(MAKEWORD(2,2),&startup)!=0) return 2;
    int failed=0;
    auto check=[&](bool ok,const std::string& name) {std::cout << "CHECK " << name << ' ' << (ok?"PASS":"FAIL") << '\n'; if(!ok)++failed;};
    const uint16_t protected_ports[]={8332,18332,18443,18444,28332,28333,8333,18333,38332,38333,18766,18445,8334,28334,19334,19335,19443,19444,29334,29335,48332,48333};
    for(uint16_t port:protected_ports) {
        std::array<unsigned char,modelnet::MODEL_LAN_BEACON_SIZE> wire{};
        check(modelnet::IsForbiddenControlPort(port)&&!modelnet::EncodeLanBeacon(Beacon(port),wire),"protected_port_"+std::to_string(port));
    }
    std::array<unsigned char,modelnet::MODEL_LAN_BEACON_SIZE> wire{}; modelnet::LanBeacon decoded;
    check(modelnet::EncodeLanBeacon(Beacon(30001),wire)&&modelnet::DecodeLanBeacon(wire.data(),wire.size(),"regtest",decoded)&&decoded.port==30001,"ordinary_codec");
    const auto ip=Interface();
    if(ip.empty()) {std::cout<<"NO_ELIGIBLE_PRIVATE_INTERFACE\n";WSACleanup();return failed?1:77;}
    const bool multicast=Discover(ip,true);check(multicast,"real_multicast_hint");
    if(!multicast)std::cout<<"BASIC_UDP_CONTROL multicast=1 observed="<<BasicUdp(ip,true)<<'\n';
    const bool unicast=Discover(ip,false);check(unicast,"real_unicast_hint");
    if(!unicast)std::cout<<"BASIC_UDP_CONTROL multicast=0 observed="<<BasicUdp(ip,false)<<'\n';
    WSACleanup(); return failed?1:0;
}
