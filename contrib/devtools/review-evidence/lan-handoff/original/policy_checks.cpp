// Synthetic ancillary/interface cases, not native topology qualification.
// The separate regression.py exercises actual helper processes and kernel metadata.
#include <algorithm>
#include <array>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <map>
#include <mutex>
#include <string>
#include <vector>
#include <arpa/inet.h>
#include <fcntl.h>
#include <ifaddrs.h>
#include <net/if.h>
#include <net/if_dl.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>
#include <iostream>
#define private public
#include <modelnet/native_discovery.h>
#undef private

static sockaddr_in addr, mask;
static ifaddrs iface;
static ifaddrs duplicate_iface;
static unsigned int current_index = 7;
static bool present = true;
static std::array<unsigned char, 48> frame;
static uint32_t packet_source, packet_destination;
static unsigned int packet_index;
static int packet_flags;
static bool delivered, include_index, include_destination;
static int FixtureGetifaddrs(ifaddrs** out) { *out = present ? &iface : nullptr; return 0; }
static void FixtureFreeifaddrs(ifaddrs*) {}
static unsigned int FixtureIndex(const char* name) { return std::string(name) == "duplicate" ? 8 : current_index; }
static ssize_t FixtureSendto(int, const void*, size_t, int, const sockaddr*, socklen_t) { return -1; }
static ssize_t FixtureRecvmsg(int, msghdr* msg, int)
{
    if (delivered) return -1;
    delivered = true;
    auto* from = static_cast<sockaddr_in*>(msg->msg_name);
    *from = {}; from->sin_family = AF_INET; from->sin_addr.s_addr = packet_source;
    msg->msg_namelen = sizeof(*from);
    std::memcpy(msg->msg_iov[0].iov_base, frame.data(), frame.size());
    msg->msg_flags = packet_flags;
    size_t used = 0;
    auto add = [&](int type, const void* data, size_t n) {
        auto* c = reinterpret_cast<cmsghdr*>(static_cast<unsigned char*>(msg->msg_control) + used);
        c->cmsg_level = IPPROTO_IP; c->cmsg_type = type; c->cmsg_len = CMSG_LEN(n);
        std::memcpy(CMSG_DATA(c), data, n); used += CMSG_SPACE(n);
    };
    if (include_index) {
        sockaddr_dl link{}; link.sdl_family = AF_LINK; link.sdl_index = packet_index;
        add(IP_RECVIF, &link, sizeof(link));
    }
    if (include_destination) {
        in_addr destination{}; destination.s_addr = packet_destination;
        add(IP_RECVDSTADDR, &destination, sizeof(destination));
    }
    msg->msg_controllen = used;
    return frame.size();
}
#define getifaddrs FixtureGetifaddrs
#define freeifaddrs FixtureFreeifaddrs
#define if_nametoindex FixtureIndex
#define recvmsg FixtureRecvmsg
#define sendto FixtureSendto
#ifndef DISCOVERY_IMPLEMENTATION
#define DISCOVERY_IMPLEMENTATION "candidate/src/modelnet/native_discovery.cpp"
#endif
#include DISCOVERY_IMPLEMENTATION
#undef sendto
#undef recvmsg
#undef if_nametoindex
#undef freeifaddrs
#undef getifaddrs

static uint32_t Ip(const char* s) { in_addr a{}; inet_pton(AF_INET, s, &a); return a.s_addr; }
int main()
{
    int failures = 0, cases = 0;
    auto run = [&](const char* name, bool want, const char* source = "10.8.0.2",
                   unsigned int index = 7, const char* destination = "239.192.0.35",
                   bool has_index = true, bool has_destination = true, int flags = 0,
                   bool has_interface = true, unsigned int interface_flags = IFF_UP | IFF_MULTICAST,
                   const char* netmask = "255.255.255.0", unsigned int enumerated_index = 7,
                   bool duplicate_address = false) {
        addr = {}; addr.sin_family = AF_INET; addr.sin_addr.s_addr = Ip("10.8.0.1");
        mask = {}; mask.sin_family = AF_INET; mask.sin_addr.s_addr = Ip(netmask);
        iface = {}; iface.ifa_addr = reinterpret_cast<sockaddr*>(&addr);
        iface.ifa_netmask = reinterpret_cast<sockaddr*>(&mask);
        iface.ifa_name = const_cast<char*>("fixture"); iface.ifa_flags = interface_flags;
        duplicate_iface = iface; duplicate_iface.ifa_name = const_cast<char*>("duplicate");
        if (duplicate_address) iface.ifa_next = &duplicate_iface;
        current_index = enumerated_index;
        present = has_interface;
        packet_source = Ip(source); packet_index = index; packet_destination = Ip(destination);
        include_index = has_index; include_destination = has_destination; packet_flags = flags; delivered = false;
        modelnet::LanBeacon beacon; beacon.network = "regtest"; beacon.port = 40002; beacon.instance.fill(7);
        if (!modelnet::EncodeLanBeacon(beacon, frame)) return false;
        modelnet::NativeLanDiscovery discovery;
        discovery.m_fd = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
        if (discovery.m_fd < 0) return false;
        discovery.m_self.network = "regtest"; discovery.m_self.instance.fill(1);
        discovery.m_interfaces.push_back({Ip("10.8.0.1"), 7});
        discovery.m_last_announce = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count();
        discovery.Tick();
        const bool got = !discovery.Endpoints().empty();
        ++cases; failures += got != want;
        std::cout << name << ' ' << (got == want ? "PASS" : "FAIL") << '\n';
        return got == want;
    };
    run("selected_group", true);
    run("selected_unicast", true, "10.8.0.2", 7, "10.8.0.1");
    run("wrong_receive_interface", false, "10.8.0.2", 8);
    run("off_subnet_private_source", false, "10.9.0.2");
    run("wrong_destination", false, "10.8.0.2", 7, "10.8.0.99");
    run("missing_receive_interface", false, "10.8.0.2", 7, "239.192.0.35", false);
    run("missing_destination", false, "10.8.0.2", 7, "239.192.0.35", true, false);
    run("truncated_ancillary", false, "10.8.0.2", 7, "239.192.0.35", true, true, MSG_CTRUNC);
    run("truncated_datagram", false, "10.8.0.2", 7, "239.192.0.35", true, true, MSG_TRUNC);
    run("interface_removed", false, "10.8.0.2", 7, "239.192.0.35", true, true, 0, false);
    run("interface_down", false, "10.8.0.2", 7, "239.192.0.35", true, true, 0, true, IFF_MULTICAST);
    run("loopback_ineligible", false, "10.8.0.2", 7, "239.192.0.35", true, true, 0, true, IFF_UP | IFF_MULTICAST | IFF_LOOPBACK);
    run("noncontiguous_mask", false, "10.8.0.2", 7, "239.192.0.35", true, true, 0, true, IFF_UP | IFF_MULTICAST, "255.0.255.0");
    run("address_moved_to_unjoined_interface", false, "10.8.0.2", 8, "239.192.0.35", true, true, 0, true, IFF_UP | IFF_MULTICAST, "255.255.255.0", 8);
    run("address_duplicated_on_unjoined_interface", false, "10.8.0.2", 8, "239.192.0.35", true, true, 0, true, IFF_UP | IFF_MULTICAST, "255.255.255.0", 7, true);
    std::cout << "cases=" << cases << " failures=" << failures << '\n';
    return failures ? 1 : 0;
}
