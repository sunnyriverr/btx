// Benign finite fixture: ordinary staged-file activity, no resource stress.
#include <windows.h>
#include <filesystem>
#include <array>
#include <string>
#include <stdexcept>
namespace fs=std::filesystem;
void Require(bool ok,const char* op){if(!ok)throw std::runtime_error(op);}
void Put(const wchar_t* path,const char* body,DWORD n)
{
    HANDLE h=CreateFileW(path,GENERIC_WRITE,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,
        nullptr,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
    Require(h!=INVALID_HANDLE_VALUE,"create");DWORD written=0;
    const bool ok=WriteFile(h,body,n,&written,nullptr)&&written==n&&FlushFileBuffers(h);
    const bool closed=CloseHandle(h)!=0;Require(ok&&closed,"write");
}
void Phase(const char* text)
{
    Put(L"phase.tmp",text,static_cast<DWORD>(std::char_traits<char>::length(text)));
    Require(MoveFileExW(L"phase.tmp",L"phase.txt",MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)!=0,"phase");
}
void Wait(const wchar_t* marker)
{
    const ULONGLONG start=GetTickCount64();
    while(GetFileAttributesW(marker)==INVALID_FILE_ATTRIBUTES){
        Require(GetFileAttributesW(L"abort")==INVALID_FILE_ATTRIBUTES,"host-abort");
        Require(GetTickCount64()-start<10000,"marker-timeout");Sleep(5);
    }
}
int main()
{
    HANDLE writer=INVALID_HANDLE_VALUE;
    try {
        Require(CreateDirectoryW(L"moving",nullptr)!=0,"mkdir-moving");
        Require(CreateDirectoryW(L"doomed",nullptr)!=0,"mkdir-doomed");
        Put(L"moving\\seed.bin","abc",3);Phase("ready");Wait(L"go.write");
        // Deliberately normal exclusive writing; monitor must not read contents.
        writer=CreateFileW(L"live.bin",GENERIC_WRITE,0,nullptr,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
        Require(writer!=INVALID_HANDLE_VALUE,"open-writer");
        std::array<char,4096> data{};data.fill('B');DWORD n=0;
        Require(WriteFile(writer,data.data(),static_cast<DWORD>(data.size()),&n,nullptr)!=0&&n==data.size(),"live-write");
        Require(FlushFileBuffers(writer)!=0,"live-flush");Phase("writer-open");Wait(L"go.rename");
        Require(MoveFileExW(L"moving",L"moved",MOVEFILE_WRITE_THROUGH)!=0,"rename-open-directory");
        Require(RemoveDirectoryW(L"doomed")!=0,"delete-open-directory");
        Put(L"ephemeral.bin","x",1);Require(DeleteFileW(L"ephemeral.bin")!=0,"delete-file");
        Phase("renamed");Wait(L"go.close");
        Require(CloseHandle(writer)!=0,"close-writer");writer=INVALID_HANDLE_VALUE;
        Phase("closed");Wait(L"go.finish");Put(L"result.txt","DONE",4);return 0;
    } catch(const std::exception& e) {
        if(writer!=INVALID_HANDLE_VALUE)CloseHandle(writer);
        try{Put(L"worker-error.txt",e.what(),static_cast<DWORD>(std::char_traits<char>::length(e.what())));}catch(...){}
        return 2;
    }
}
