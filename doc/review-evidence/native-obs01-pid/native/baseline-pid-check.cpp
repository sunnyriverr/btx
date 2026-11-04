#include <util/fs.h>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#ifdef _WIN32
#include <windows.h>
#endif
#include <unistd.h>
struct TempTree {
    fs::path root;
    explicit TempTree(const fs::path& path) : root(path) {}
    ~TempTree()
    {
        std::error_code ec;
        fs::remove_all(root, ec);
    }
};
int checks=0, failures=0;
void check(bool ok,const char* name){++checks;if(!ok){++failures;std::cerr<<"FAIL "<<name<<"\n";}}
int main(int argc,char** argv){
 try{
  if(argc!=2)return 2;
  const fs::path owned=fs::u8path(argv[1]);
  if(!std::filesystem::equivalent(fs::temp_directory_path(),owned))return 2;
#ifdef _WIN32
  const auto oracle=static_cast<unsigned long long>(::GetCurrentProcessId());
#else
  const auto oracle=static_cast<unsigned long long>(::getpid());
#endif
  check(oracle>0,"PID is nonzero");
  std::cout<<"PID oracle="<<oracle<<"\n";
  const fs::path expected=owned/fs::u8path("btx-obs01-"+std::to_string(oracle));
  const fs::path sibling=owned/"unrelated-sentinel";
  {std::ofstream out(sibling);out<<"keep";if(!out.good())return 2;}
  std::string prior;
  for(int mode=0;mode<3;++mode){
   check(!fs::exists(expected),"tree absent before owned case");
   auto scope=[&]() -> int {
        const TempTree tree{fs::temp_directory_path() / ("btx-obs01-" + std::to_string(::getpid()))};
    if(tree.root.lexically_normal()!=expected.lexically_normal()){
     check(false,"PID-derived exact prefix/suffix");return 9;
    }
    check(true,"PID-derived exact prefix/suffix");
    const auto current=tree.root.filename().utf8string();
    check(mode==0||prior==current,"stable same-process name");prior=current;
    check(fs::create_directories(tree.root/"nested"),"owned directory create");
    {std::ofstream out(tree.root/"nested"/"payload");out<<"test";check(out.good(),"owned content write");}
    check(fs::is_regular_file(tree.root/"nested"/"payload"),"owned content exists");
    if(mode==1)return 37;
    if(mode==2)throw 314;
    return 0;
   };
   int result=0;
   try{result=scope();check(mode!=2,"expected exception reached");}
   catch(int code){check(mode==2&&code==314,"exception propagated");result=0;}
   check(result==(mode==1?37:0),"normal/early-return result");
   check(!fs::exists(expected),"owned tree cleanup");
   check(fs::is_regular_file(sibling),"unrelated sibling retained");
   check(fs::is_directory(owned),"owned parent retained");
  }
  std::ifstream input(sibling);std::string text;input>>text;check(text=="keep","sibling bytes retained");input.close();
  check(fs::remove(sibling),"fixture sentinel cleanup");
  check(fs::is_empty(owned),"fixture parent empty");
  std::cout<<"RESULT checks="<<checks<<" failures="<<failures<<"\n";
  return failures?1:0;
 }catch(const std::exception& e){std::cerr<<"SETUP "<<e.what()<<"\n";return 2;}
}
