#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif

#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
// The other Windows headers model plane files include. They use macros
// removed below (VOID, CALLBACK, interface), so they are read first.
#include <aclapi.h>
#include <bcrypt.h>
#include <iphlpapi.h>
#include <mswsock.h>
#include <objbase.h>
#include <sddl.h>
#include <userenv.h>

// Windows headers macro-define identifiers the node and the lab use as enums.
#ifdef STRICT
#undef STRICT
#endif
#ifdef IGNORE
#undef IGNORE
#endif
#ifdef ERROR
#undef ERROR
#endif
#ifdef IN
#undef IN
#endif
#ifdef OUT
#undef OUT
#endif
#ifdef OPTIONAL
#undef OPTIONAL
#endif
#ifdef DIFFERENCE
#undef DIFFERENCE
#endif
#ifdef ABSOLUTE
#undef ABSOLUTE
#endif
#ifdef RELATIVE
#undef RELATIVE
#endif
#ifdef DELETE
#undef DELETE
#endif
#ifdef CONST
#undef CONST
#endif
#ifdef VOID
#undef VOID
#endif
#ifdef CALLBACK
#undef CALLBACK
#endif
#ifdef interface
#undef interface
#endif
// FAR/NEAR use the empty Win32 far/near macros. Preserve their SDK
// meaning when removing the lowercase macros used as BTX identifiers.
#undef FAR
#define FAR
#undef NEAR
#define NEAR
#ifdef near
#undef near
#endif
#ifdef far
#undef far
#endif
#ifdef pascal
#undef pascal
#endif


#include <mswsock.h>
LPFN_WSARECVMSG receiver = nullptr;
GUID receive_id = WSAID_WSARECVMSG;
IN_PKTINFO packet_info{};
group_req membership{};
int main() { return receiver == nullptr && packet_info.ipi_ifindex == 0 && membership.gr_interface == 0 ? 0 : 1; }
