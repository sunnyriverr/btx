// API feasibility fixture only; not the production accounting implementation.
#include <windows.h>
#include <tlhelp32.h>
#include <modelnet/swarm_fsjail.h>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <array>
#include <vector>
#include <map>
#include <string>
#include <functional>
#include <stdexcept>
#include <thread>
#include <cstddef>
#include <limits>
struct Handle {
    HANDLE h{INVALID_HANDLE_VALUE};
    Handle()=default;explicit Handle(HANDLE v):h(v){}
    ~Handle(){reset();}Handle(const Handle&)=delete;Handle& operator=(const Handle&)=delete;
    Handle(Handle&& o)noexcept:h(o.h){o.h=INVALID_HANDLE_VALUE;}
    Handle& operator=(Handle&& o)noexcept{if(this!=&o){reset();h=o.h;o.h=INVALID_HANDLE_VALUE;}return *this;}
    void reset(){if(h!=INVALID_HANDLE_VALUE&&h!=nullptr)CloseHandle(h);h=INVALID_HANDLE_VALUE;}
    bool valid()const{return h!=INVALID_HANDLE_VALUE&&h!=nullptr;}
};
[[noreturn]] void Error(const std::string& op){throw std::runtime_error(op+":win32="+std::to_string(GetLastError()));}
void Check(bool ok,const std::string& op){if(!ok)throw std::runtime_error(op);}
void Pass(const std::string& name,const std::string& detail=""){std::cout<<"CHECK "<<name<<" PASS "<<detail<<std::endl;}
std::string Read(const fs::path& p)
{
    Handle h(CreateFileW(p.c_str(),GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,
        nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr));
    if(!h.valid()){
        const DWORD error=GetLastError();if(error==ERROR_FILE_NOT_FOUND||error==ERROR_PATH_NOT_FOUND)return {};
        SetLastError(error);Error("fixture-read-open");
    }
    std::array<char,8192> bytes{};DWORD n=0;if(!ReadFile(h.h,bytes.data(),static_cast<DWORD>(bytes.size()),&n,nullptr))Error("fixture-read");
    Check(n<bytes.size(),"fixture-read-bound");return std::string(bytes.data(),n);
}
bool Missing(const fs::path& p)
{
    if(GetFileAttributesW(p.c_str())!=INVALID_FILE_ATTRIBUTES)return false;
    const DWORD error=GetLastError();return error==ERROR_FILE_NOT_FOUND||error==ERROR_PATH_NOT_FOUND;
}
void Put(const fs::path& p){std::ofstream f(p,std::ios::binary);f<<"go";f.close();Check(!f.fail(),"host-marker");}
void WaitPhase(const fs::path& root,const std::string& phase)
{
    const auto start=GetTickCount64();
    while(Read(root/L"phase.txt")!=phase){Check(GetTickCount64()-start<10000,"phase-timeout:"+phase);Sleep(5);}
}
std::wstring FinalPath(HANDLE h)
{
    std::array<wchar_t,32768> b{};DWORD n=GetFinalPathNameByHandleW(h,b.data(),static_cast<DWORD>(b.size()),FILE_NAME_NORMALIZED|VOLUME_NAME_DOS);
    if(!n||n>=b.size())Error("final-path");std::wstring p(b.data(),n);
    while(p.size()>4&&p.back()==L'\\')p.pop_back();return p;
}
bool Below(const std::wstring& path,const std::wstring& root)
{
    return path.size()>root.size()&&path[root.size()]==L'\\'&&
        CompareStringOrdinal(path.data(),static_cast<int>(root.size()),root.data(),static_cast<int>(root.size()),TRUE)==CSTR_EQUAL;
}
BY_HANDLE_FILE_INFORMATION Info(HANDLE h)
{
    BY_HANDLE_FILE_INFORMATION i{};if(!GetFileInformationByHandle(h,&i))Error("handle-info");return i;
}
uint64_t Id(const BY_HANDLE_FILE_INFORMATION& i){return (uint64_t(i.nFileIndexHigh)<<32)|i.nFileIndexLow;}
using Visit=std::function<void(const FILE_ID_BOTH_DIR_INFO&,const std::wstring&)>;
void Entries(HANDLE directory,const Visit& visit)
{
    alignas(FILE_ID_BOTH_DIR_INFO) std::array<unsigned char,65536> bytes{};
    size_t batches=0;
    for(;;){
        Check(++batches<=8192,"enumeration-batch-bound");bytes.fill(0);
        if(!GetFileInformationByHandleEx(directory,FileIdBothDirectoryInfo,bytes.data(),static_cast<DWORD>(bytes.size()))){
            if(GetLastError()==ERROR_NO_MORE_FILES)return;Error("directory-enumeration");
        }
        size_t offset=0;
        for(;;){
            Check(offset+offsetof(FILE_ID_BOTH_DIR_INFO,FileName)<=bytes.size(),"record-header-bound");
            const auto* item=reinterpret_cast<const FILE_ID_BOTH_DIR_INFO*>(bytes.data()+offset);
            Check(item->FileNameLength%sizeof(wchar_t)==0&&item->FileNameLength<=bytes.size()-offset- offsetof(FILE_ID_BOTH_DIR_INFO,FileName),"record-name-bound");
            std::wstring name(item->FileName,item->FileNameLength/sizeof(wchar_t));
            if(name!=L"."&&name!=L"..")visit(*item,name);
            if(!item->NextEntryOffset)break;
            Check(item->NextEntryOffset>=offsetof(FILE_ID_BOTH_DIR_INFO,FileName)&&item->NextEntryOffset<=bytes.size()-offset,"record-next-bound");
            offset+=item->NextEntryOffset;
        }
    }
}
Handle OpenId(HANDLE root,const FILE_ID_BOTH_DIR_INFO& e,const std::wstring& anchor,DWORD volume)
{
    FILE_ID_DESCRIPTOR id{};id.dwSize=sizeof(id);id.Type=FileIdType;id.FileId=e.FileId;
    const bool directory=(e.FileAttributes&FILE_ATTRIBUTE_DIRECTORY)!=0;
    Handle h(OpenFileById(root,&id,directory?FILE_LIST_DIRECTORY:0,
        FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,nullptr,FILE_FLAG_BACKUP_SEMANTICS|FILE_FLAG_OPEN_REPARSE_POINT));
    if(!h.valid())Error(directory?"open-directory-by-id":"open-file-by-id");
    const auto info=Info(h.h);
    Check(info.dwVolumeSerialNumber==volume&&Id(info)==static_cast<uint64_t>(e.FileId.QuadPart),"identity-volume");
    Check(!(info.dwFileAttributes&FILE_ATTRIBUTE_REPARSE_POINT),"reparse-refused");
    Check(((info.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY)!=0)==directory,"type-stable");
    Check(Below(FinalPath(h.h),anchor),"root-membership");return h;
}
struct Sample {uint64_t bytes{0};size_t entries{0};std::map<std::wstring,uint64_t> files;std::map<std::wstring,uint64_t> directory_lengths;};
void Walk(HANDLE root,HANDLE directory,const std::wstring& anchor,DWORD volume,size_t depth,Sample& out)
{
    Check(depth<=64,"depth-bound");
    Entries(directory,[&](const FILE_ID_BOTH_DIR_INFO& item,const std::wstring&){
        Check(++out.entries<=8192,"entry-bound");Check(!(item.FileAttributes&FILE_ATTRIBUTE_REPARSE_POINT),"entry-reparse-refused");
        auto h=OpenId(root,item,anchor,volume);const std::wstring relative=FinalPath(h.h).substr(anchor.size()+1);
        if(item.FileAttributes&FILE_ATTRIBUTE_DIRECTORY){Walk(root,h.h,anchor,volume,depth+1,out);return;}
        FILE_STANDARD_INFO standard{};if(!GetFileInformationByHandleEx(h.h,FileStandardInfo,&standard,sizeof(standard)))Error("file-standard-info");
        Check(!standard.Directory&&!standard.DeletePending&&standard.NumberOfLinks==1&&standard.EndOfFile.QuadPart>=0,"regular-file-metadata");
        const uint64_t size=static_cast<uint64_t>(standard.EndOfFile.QuadPart);
        Check(size<=std::numeric_limits<uint64_t>::max()-out.bytes,"sum-overflow");out.bytes+=size;
        Check(out.files.emplace(relative,size).second,"duplicate-identity-path");
        Check(item.EndOfFile.QuadPart>=0,"directory-record-size");out.directory_lengths[relative]=static_cast<uint64_t>(item.EndOfFile.QuadPart);
    });
}
Handle OpenRoot(const fs::path& root)
{
    Handle h(CreateFileW(root.c_str(),FILE_LIST_DIRECTORY,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,
        nullptr,OPEN_EXISTING,FILE_FLAG_BACKUP_SEMANTICS|FILE_FLAG_OPEN_REPARSE_POINT,nullptr));
    if(!h.valid())Error("open-root");const auto i=Info(h.h);
    Check((i.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY)&&!(i.dwFileAttributes&FILE_ATTRIBUTE_REPARSE_POINT),"root-type");return h;
}
Sample Scan(const fs::path& root)
{
    auto h=OpenRoot(root);Sample result;Walk(h.h,h.h,FinalPath(h.h),Info(h.h).dwVolumeSerialNumber,0,result);return result;
}
Handle HoldDirectory(const fs::path& root,const std::wstring& name)
{
    auto r=OpenRoot(root);Handle held;const auto anchor=FinalPath(r.h);const auto volume=Info(r.h).dwVolumeSerialNumber;
    Entries(r.h,[&](const FILE_ID_BOTH_DIR_INFO& e,const std::wstring& n){if(n==name){Check((e.FileAttributes&FILE_ATTRIBUTE_DIRECTORY)!=0,"hold-directory-type");held=OpenId(r.h,e,anchor,volume);}});
    Check(held.valid(),"directory-not-found");return held;
}
fs::path FindOwnedChildRoot()
{
    const auto start=GetTickCount64();
    while(GetTickCount64()-start<20000){
        Handle list(CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS,0));if(!list.valid())Error("process-snapshot");
        PROCESSENTRY32W entry{};entry.dwSize=sizeof(entry);
        if(Process32FirstW(list.h,&entry))do{
            if(entry.th32ParentProcessID!=GetCurrentProcessId()||_wcsicmp(entry.szExeFile,L"worker.exe"))continue;
            Handle child(OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION|SYNCHRONIZE,FALSE,entry.th32ProcessID));
            if(!child.valid())continue;std::array<wchar_t,32768> image{};DWORD n=static_cast<DWORD>(image.size());
            if(!QueryFullProcessImageNameW(child.h,0,image.data(),&n))continue;
            fs::path executable(std::wstring(image.data(),n));const auto root=executable.parent_path();
            std::cout<<"CHILD_IMAGE_ROOT "<<root.utf8string()<<std::endl;
            Check(root.filename()==L"work"&&root.parent_path().filename().wstring().starts_with(L"btx.native."),"owned-profile-layout");
            std::cout<<"OWNED_CHILD "<<entry.th32ProcessID<<std::endl;return root;
        }while(Process32NextW(list.h,&entry));Sleep(5);
    }
    throw std::runtime_error("owned-child-not-observed");
}
void Probe(const fs::path& root)
{
    WaitPhase(root,"ready");auto root_handle=OpenRoot(root);
    std::array<wchar_t,128> filesystem{};DWORD serial=0,component=0,flags=0;
    if(!GetVolumeInformationByHandleW(root_handle.h,nullptr,0,&serial,&component,&flags,filesystem.data(),static_cast<DWORD>(filesystem.size())))Error("volume-information");
    const std::wstring fs_name(filesystem.data());std::cout<<"FILESYSTEM "<<std::string(fs_name.begin(),fs_name.end())<<std::endl;
    auto moving=HoldDirectory(root,L"moving"),doomed=HoldDirectory(root,L"doomed");
    auto initial=Scan(root);Check(initial.files.at(L"moving\\seed.bin")==3,"initial-size");Pass("initial-nested-enumeration");
    Put(root/L"go.write");WaitPhase(root,"writer-open");
    auto live=Scan(root);Check(live.files.at(L"live.bin")==4096,"live-handle-size");
    Pass("exclusive-writer-live-size","handle=4096 directory-record="+std::to_string(live.directory_lengths.at(L"live.bin")));
    Handle reader(CreateFileW((root/L"live.bin").c_str(),GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,0,nullptr));
    Check(!reader.valid()&&GetLastError()==ERROR_SHARING_VIOLATION,"exclusive-writer-control");Pass("content-reader-sharing-control");
    Put(root/L"go.rename");WaitPhase(root,"renamed");
    const auto path=FinalPath(moving.h);Check(path.ends_with(L"\\moved"),"renamed-handle-path");
    Pass("directory-rename-with-monitor-handle");
    FILE_STANDARD_INFO deleted{};
    if(!GetFileInformationByHandleEx(doomed.h,FileStandardInfo,&deleted,sizeof(deleted)))Error("deleted-directory-info");
    Check(deleted.DeletePending!=FALSE,"directory-delete-pending");doomed.reset();
    Check(Missing(root/L"doomed"),"directory-deleted");
    Check(Missing(root/L"ephemeral.bin"),"file-deleted");Pass("directory-and-file-deletion");
    moving.reset();auto renamed=Scan(root);
    Check(renamed.files.at(L"moved\\seed.bin")==3&&renamed.files.at(L"live.bin")==4096,"post-rename-sizes");
    Check(!renamed.files.contains(L"moving\\seed.bin"),"old-name-absent");Pass("post-rename-rescan");
    Put(root/L"go.close");WaitPhase(root,"closed");auto closed=Scan(root);
    Check(closed.files.at(L"live.bin")==4096&&Read(root/L"live.bin")==std::string(4096,'B'),"closed-content");
    Pass("closed-file-content-and-size");root_handle.reset();Put(root/L"go.finish");
}
int wmain(int argc,wchar_t** argv)
{
    if(argc!=3)return 2;const fs::path original=fs::absolute(argv[1]);const fs::path helper=fs::absolute(argv[2]);
    modelnet::SwarmFilesystemJailRequest request;request.root=original;request.helper=helper;
    request.network_denied=true;request.max_wall_seconds=60;request.max_tree_bytes=4ULL*1024*1024;
    fs::path staged;std::string monitor_error;bool monitor_ok=false;
    std::thread monitor([&]{try{staged=FindOwnedChildRoot();std::cout<<"STAGED_ROOT "<<staged.utf8string()<<std::endl;Probe(staged);monitor_ok=true;}catch(const std::exception& e){monitor_error=e.what();if(!staged.empty())try{Put(staged/L"abort");}catch(...){};}});
    std::string error,backend_exception;modelnet::SwarmFilesystemJailResult run;
    try{run=modelnet::SwarmRunFilesystemJail(request,error);}catch(const std::exception& e){backend_exception=e.what();}catch(...){backend_exception="unknown-backend-exception";}
    monitor.join();
    std::cout<<"BACKEND "<<run.code<<" launched="<<run.launched<<" jailed="<<run.jailed<<" child="<<run.child_status<<" error="<<error<<std::endl;
    if(!monitor_error.empty())std::cout<<"PROBE_ERROR "<<monitor_error<<std::endl;
    if(!backend_exception.empty())std::cout<<"BACKEND_EXCEPTION "<<backend_exception<<std::endl;
    try{
        Check(!staged.empty(),"staged-root-observed");Check(!fs::exists(staged),"owned-staged-root-cleanup");Pass("owned-staged-root-cleanup");
        Check(backend_exception.empty()&&monitor_ok,"monitor-feasibility-not-established");
        Check(run.launched&&run.jailed&&run.child_status==0&&run.code=="JAILED","native-worker-result");
        Check(Read(original/L"result.txt")=="DONE"&&Read(original/L"live.bin")==std::string(4096,'B'),"published-output");Pass("real-backend-output");
        std::cout<<"VERDICT PASS"<<std::endl;return 0;
    }catch(const std::exception& e){std::cout<<"VERDICT NOT_FEASIBLE "<<e.what()<<std::endl;return 1;}
}
