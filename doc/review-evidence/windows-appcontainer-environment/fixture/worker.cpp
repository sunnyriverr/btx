// Finite legitimate-output fixture. No arguments, network or model.
#include <windows.h>
#include <array>
int main()
{
    HANDLE out=CreateFileW(L"result.bin",GENERIC_WRITE,0,nullptr,CREATE_NEW,
                           FILE_ATTRIBUTE_NORMAL,nullptr);
    if(out==INVALID_HANDLE_VALUE)return 2;
    std::array<unsigned char,512> bytes{};
    bytes.fill(0x42);
    DWORD written=0;
    const bool ok=WriteFile(out,bytes.data(),static_cast<DWORD>(bytes.size()),&written,nullptr)!=0 &&
        written==bytes.size() && FlushFileBuffers(out)!=0;
    const bool closed=CloseHandle(out)!=0;
    return ok && closed ? 0 : 3;
}
