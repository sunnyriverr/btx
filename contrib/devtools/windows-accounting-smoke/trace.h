// Diagnostic-only API observation: arguments/results and last-error are preserved.
#include <windows.h>
#include <cstdio>
inline BOOL WINAPI BtxTraceUpdateAttribute(LPPROC_THREAD_ATTRIBUTE_LIST list,DWORD flags,
    DWORD_PTR attribute,PVOID value,SIZE_T size,PVOID previous,PSIZE_T returned)
{
    const BOOL ok=UpdateProcThreadAttribute(list,flags,attribute,value,size,previous,returned);
    const DWORD error=GetLastError();
    std::fprintf(stderr,"WIN32TRACE UpdateProcThreadAttribute attribute=%llu ok=%d error=%lu\n",
        static_cast<unsigned long long>(attribute),static_cast<int>(ok),static_cast<unsigned long>(error));
    SetLastError(error);return ok;
}
inline BOOL WINAPI BtxTraceCreateProcess(LPCWSTR application,LPWSTR command,
    LPSECURITY_ATTRIBUTES process_security,LPSECURITY_ATTRIBUTES thread_security,
    BOOL inherit,DWORD flags,LPVOID environment,LPCWSTR directory,
    LPSTARTUPINFOW startup,LPPROCESS_INFORMATION information)
{
    const BOOL ok=CreateProcessW(application,command,process_security,thread_security,
        inherit,flags,environment,directory,startup,information);
    const DWORD error=GetLastError();
    std::fprintf(stderr,"WIN32TRACE CreateProcessW ok=%d error=%lu\n",
        static_cast<int>(ok),static_cast<unsigned long>(error));
    SetLastError(error);return ok;
}
#define UpdateProcThreadAttribute BtxTraceUpdateAttribute
#define CreateProcessW BtxTraceCreateProcess
