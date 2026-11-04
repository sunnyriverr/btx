// Diagnostic-only API observation: arguments/results and last-error are preserved.
#include <windows.h>
#include <cstdio>
#include <string>
#include <vector>
#include <algorithm>
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
    std::vector<wchar_t> probe;
    // Explicit test-only single-variable differential. Default path is unchanged.
    // This does not copy the parent environment or alter capabilities/Job policy.
    if(GetEnvironmentVariableW(L"BTX_ACCOUNTING_LOCALAPPDATA_CONTROL",nullptr,0)>0) {
        wchar_t local[32768];
        const DWORD length=GetEnvironmentVariableW(L"LOCALAPPDATA",local,32768);
        if(length>0 && length<32768 && environment && (flags&CREATE_UNICODE_ENVIRONMENT)) {
            std::vector<std::wstring> entries;
            for(const wchar_t* item=static_cast<const wchar_t*>(environment);*item;item+=wcslen(item)+1)
                entries.emplace_back(item);
            entries.emplace_back(std::wstring(L"LOCALAPPDATA=")+local);
            std::sort(entries.begin(),entries.end(),[](const auto& a,const auto& b){return _wcsicmp(a.c_str(),b.c_str())<0;});
            for(const auto& entry:entries){probe.insert(probe.end(),entry.begin(),entry.end());probe.push_back(0);}
            probe.push_back(0);environment=probe.data();
            std::fprintf(stderr,"WIN32TRACE test-only environment adds LOCALAPPDATA; value omitted\n");
        }
    }
    const BOOL ok=CreateProcessW(application,command,process_security,thread_security,
        inherit,flags,environment,directory,startup,information);
    const DWORD error=GetLastError();
    std::fprintf(stderr,"WIN32TRACE CreateProcessW ok=%d error=%lu\n",
        static_cast<int>(ok),static_cast<unsigned long>(error));
    SetLastError(error);return ok;
}
#define UpdateProcThreadAttribute BtxTraceUpdateAttribute
#define CreateProcessW BtxTraceCreateProcess
