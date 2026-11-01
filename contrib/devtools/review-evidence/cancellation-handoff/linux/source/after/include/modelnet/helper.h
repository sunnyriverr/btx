#pragma once
#include <util/fs.h>
#include <univalue.h>
#include <atomic>
namespace modelnet {
fs::path UnixRpcListenPath(const fs::path&);
bool UnixSocketSafeToAdopt(const fs::path&,std::string&);
bool UnixConnectedPeerIsSelf(int,std::string&);
void SetNodeModelHostAdvertised(bool);
bool CallUnixRpc(const fs::path&,const std::string&,const UniValue&,UniValue&,std::string&,std::atomic<bool>* =nullptr,bool=false);
}
