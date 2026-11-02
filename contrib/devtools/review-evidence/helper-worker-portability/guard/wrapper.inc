// Windows process shims reject fork, so no worker child reaches this there.
void CloseWorkerDescriptors()
{
#ifndef _WIN32
    subprocess::detail::subprocess_close_all_fds(/*except_fd=*/-1);
#endif
}

