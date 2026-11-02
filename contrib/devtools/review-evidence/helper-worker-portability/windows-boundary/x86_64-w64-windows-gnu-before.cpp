#if (defined _MSC_VER) || (defined __MINGW32__)
  #define __USING_WINDOWS__
#endif
namespace subprocess { namespace detail {
#ifndef __USING_WINDOWS__
  void subprocess_close_all_fds(int except_fd);
#endif
}}
void launch_boundary(){subprocess::detail::subprocess_close_all_fds(-1);}
