#if (defined _MSC_VER) || (defined __MINGW32__)
  #define __USING_WINDOWS__
#endif
namespace subprocess { namespace detail {
#ifndef __USING_WINDOWS__
  void subprocess_close_all_fds(int except_fd);
#endif
}}
// Windows process shims reject fork, so no worker child reaches this there.
void CloseWorkerDescriptors()
{
#ifndef _WIN32
    subprocess::detail::subprocess_close_all_fds(/*except_fd=*/-1);
#endif
}

void launch_boundary(){CloseWorkerDescriptors();}
