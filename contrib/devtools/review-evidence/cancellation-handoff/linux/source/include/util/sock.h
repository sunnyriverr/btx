#pragma once
#include <compat/compat.h>
class Sock { SOCKET m_socket; public:explicit Sock(SOCKET s):m_socket(s){} ~Sock(){::close(m_socket);} bool SetNonBlocking() const;};
bool Sock::SetNonBlocking() const
{
#ifdef WIN32
    u_long on{1};
    if (ioctlsocket(m_socket, FIONBIO, &on) == SOCKET_ERROR) {
        return false;
    }
#else
    const int flags{fcntl(m_socket, F_GETFL, 0)};
    if (flags == SOCKET_ERROR) {
        return false;
    }
    if (fcntl(m_socket, F_SETFL, flags | O_NONBLOCK) == SOCKET_ERROR) {
        return false;
    }
#endif
    return true;
}
