#include <filesystem>
#include <string>
#include <cstdlib>
#include <stdexcept>
#include <iostream>
#include <fstream>
#include <cerrno>
#include <sys/stat.h>
#ifdef _WIN32
#define NOMINMAX
#include <windows.h>
#include <aclapi.h>
#include <sddl.h>
#include <modelnet/security_v2/common.h>
namespace security=modelnet::security;
#else
#include <unistd.h>
#endif
namespace fs {using path=std::filesystem::path;std::string PathToString(const path& p){return p.string();}}
bool EnsurePrivateDir(const fs::path& dir, std::string& err)
{
#ifdef _WIN32
    try {
        security::EnsurePrivateDirectory(dir);
        return true;
    } catch (const security::Error& e) {
        err = "cannot make private: " + fs::PathToString(dir) + ": " + e.code;
        return false;
    }
#else
    const std::string path{fs::PathToString(dir)};
    if (::mkdir(path.c_str(), 0700) != 0 && errno != EEXIST) {
        err = "cannot create " + path;
        return false;
    }
    struct stat st {};
    if (::lstat(path.c_str(), &st) != 0 || !S_ISDIR(st.st_mode) || st.st_uid != ::geteuid()) {
        err = "not a directory of this user: " + path;
        return false;
    }
    if ((st.st_mode & 077) != 0 && ::chmod(path.c_str(), 0700) != 0) {
        err = "cannot make private: " + path;
        return false;
    }
    return true;
#endif
}

int main(int argc,char** argv){try {std::cout.setf(std::ios::unitbuf);
 if(argc!=2)return 2;const fs::path root=std::filesystem::absolute(argv[1]);std::filesystem::create_directories(root);std::string err;
 auto check=[&](bool b,const char* n){if(!b)throw std::runtime_error(std::string(n)+": "+err);std::cout<<n<<" PASS\n";};
 const auto good=root/"private";check(EnsurePrivateDir(good,err),"create private directory");check(EnsurePrivateDir(good,err),"reopen private directory");
 const auto file=root/"ordinary-file";{std::ofstream out(file);out<<"retained";}check(!EnsurePrivateDir(file,err),"refuse file");
 const auto broad=root/"broad";std::filesystem::create_directory(broad);
#ifdef _WIN32
 PSECURITY_DESCRIPTOR sd=nullptr;check(ConvertStringSecurityDescriptorToSecurityDescriptorW(L"D:(A;;FA;;;WD)",SDDL_REVISION_1,&sd,nullptr),"build broad ACL fixture");BOOL present=FALSE,def=FALSE;PACL acl=nullptr;check(GetSecurityDescriptorDacl(sd,&present,&acl,&def)&&present,"read broad ACL fixture");check(SetNamedSecurityInfoW(const_cast<wchar_t*>(broad.c_str()),SE_FILE_OBJECT,DACL_SECURITY_INFORMATION|PROTECTED_DACL_SECURITY_INFORMATION,nullptr,nullptr,acl,nullptr)==ERROR_SUCCESS,"install broad ACL fixture");LocalFree(sd);check(!EnsurePrivateDir(broad,err),"refuse broad ACL directory");
 const auto link=root/"junction";const std::string cmd="cmd /c mklink /J \""+link.string()+"\" \""+good.string()+"\" >nul";check(std::system(cmd.c_str())==0,"create junction fixture");check(!EnsurePrivateDir(link,err),"refuse junction");check(!EnsurePrivateDir(link/"nested",err),"refuse junction ancestor");std::filesystem::remove(link);
#else
 ::chmod(broad.c_str(),0777);check(EnsurePrivateDir(broad,err),"tighten own directory");struct stat st{};check(::lstat(broad.c_str(),&st)==0&&(st.st_mode&077)==0,"private mode retained");const auto link=root/"symlink";std::filesystem::create_directory_symlink(good,link);check(!EnsurePrivateDir(link,err),"refuse symlink");std::filesystem::remove(link);
#endif
 check(EnsurePrivateDir(good,err),"healthy retry after refusals");std::ifstream in(file);std::string bytes;in>>bytes;check(bytes=="retained","existing file unchanged");in.close();std::filesystem::remove_all(root);return 0;
 }catch(const std::exception& e){std::cerr<<"CONTROL_FAILURE: "<<e.what()<<"\n";return 1;}}
