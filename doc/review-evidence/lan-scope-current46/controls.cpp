#include <modelnet/native_discovery.h>
#include <modelnet/model_nat.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>
#include <array>
#include <chrono>
#include <iostream>
#include <thread>

modelnet::LanBeacon Beacon(uint16_t port) {
    modelnet::LanBeacon b; b.network="regtest"; b.port=port; b.instance.fill(7); return b;
}
bool Hint(const char* ip,const char* destination,uint16_t port) {
    modelnet::NativeLanDiscovery discovery; std::string error;
    if(!discovery.Open("regtest",ip,30400,error)){std::cout<<"open="<<error<<'\n';return false;}
    auto idle=std::chrono::steady_clock::now(); discovery.Tick();
    if(std::chrono::steady_clock::now()-idle>std::chrono::milliseconds(500))return false;
    int fd=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);if(fd<0)return false;
    sockaddr_in source{};source.sin_family=AF_INET;inet_pton(AF_INET,ip,&source.sin_addr);
    if(bind(fd,reinterpret_cast<sockaddr*>(&source),sizeof(source))!=0){close(fd);return false;}
    unsigned char ttl=0,loop=1;
    if(setsockopt(fd,IPPROTO_IP,IP_MULTICAST_IF,&source.sin_addr,sizeof(source.sin_addr)) ||
       setsockopt(fd,IPPROTO_IP,IP_MULTICAST_TTL,&ttl,sizeof(ttl)) ||
       setsockopt(fd,IPPROTO_IP,IP_MULTICAST_LOOP,&loop,sizeof(loop))){close(fd);return false;}
    std::array<unsigned char,modelnet::MODEL_LAN_BEACON_SIZE> wire{};
    if(!modelnet::EncodeLanBeacon(Beacon(port),wire)){close(fd);return false;}
    sockaddr_in target{};target.sin_family=AF_INET;target.sin_port=htons(modelnet::MODEL_LAN_DISCOVERY_PORT);inet_pton(AF_INET,destination,&target.sin_addr);
    const auto sent=sendto(fd,wire.data(),wire.size(),0,reinterpret_cast<sockaddr*>(&target),sizeof(target));close(fd);
    if(sent!=static_cast<ssize_t>(wire.size()))return false;
    const std::string wanted=std::string(ip)+":"+std::to_string(port);
    for(int i=0;i<100;++i){discovery.Tick();for(const auto& endpoint:discovery.Endpoints())if(endpoint==wanted)return true;std::this_thread::sleep_for(std::chrono::milliseconds(10));}
    return false;
}
int main(int argc,char**argv){
    if(argc!=2)return 2;
    int failed=0;
    const uint16_t controls[]={8332,18332,18443,18444,28332,28333,8333,18333,38332,38333,18766,18445,8334,28334,19334,19335,19443,19444,29334,29335,48332,48333};
    for(uint16_t port:controls){
        std::array<unsigned char,modelnet::MODEL_LAN_BEACON_SIZE> wire{};modelnet::LanHintBook book;
        const bool ok=modelnet::IsForbiddenControlPort(port)&&!modelnet::EncodeLanBeacon(Beacon(port),wire)&&!book.Observe(argv[1],Beacon(port),1);
        std::cout<<"protected_port="<<port<<" pass="<<ok<<'\n';if(!ok)++failed;
    }
    for(uint16_t port:{uint16_t(30001),uint16_t(65535)}){
        std::array<unsigned char,modelnet::MODEL_LAN_BEACON_SIZE> wire{};modelnet::LanBeacon decoded;modelnet::LanHintBook book;
        const bool ok=modelnet::EncodeLanBeacon(Beacon(port),wire)&&modelnet::DecodeLanBeacon(wire.data(),wire.size(),"regtest",decoded)&&decoded.port==port&&book.Observe(argv[1],decoded,1)&&book.Endpoints(2).size()==1;
        std::cout<<"ordinary_port="<<port<<" pass="<<ok<<'\n';if(!ok)++failed;
    }
    bool multicast=Hint(argv[1],"239.192.0.35",30310);std::cout<<"valid_multicast="<<multicast<<'\n';if(!multicast)++failed;
    bool unicast=Hint(argv[1],argv[1],30311);std::cout<<"own_host_unicast_observed="<<unicast<<" (routing-dependent control)\n";
    return failed?1:0;
}
