// Finite valid-control fixture: require OS profile lookup, exclude parent sentinel.
#include <windows.h>
#include <array>
int main()
{
    if(GetEnvironmentVariableW(L"BTX_ENV_PARENT_SENTINEL",nullptr,0)!=0)return 4;
    if(GetEnvironmentVariableW(L"LOCALAPPDATA",nullptr,0)==0)return 5;
    HANDLE out=CreateFileW(L"result.bin",GENERIC_WRITE,0,nullptr,CREATE_NEW,
                           FILE_ATTRIBUTE_NORMAL,nullptr);
    if(out==INVALID_HANDLE_VALUE)return 2;
    std::array<unsigned char,512> bytes{};bytes.fill(0x42);
    DWORD written=0;
    const bool ok=WriteFile(out,bytes.data(),static_cast<DWORD>(bytes.size()),&written,nullptr)!=0 &&
        written==bytes.size() && FlushFileBuffers(out)!=0;
    const bool closed=CloseHandle(out)!=0;
    return ok && closed?0:3;
}
