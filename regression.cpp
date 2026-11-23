#include <modelnet/catalog.h>
#include <crypto/common.h>
#include <util/fs.h>
#include <util/translation.h>
#include <fstream>
#include <iostream>
#include <cstring>
#include <stdexcept>
#include <vector>
const TranslateFn G_TRANSLATION_FUN{nullptr};
fs::path m_path_root;
unsigned assertions=0, failures=0;
void check(bool ok,const char* expr,int line,bool fatal=false){++assertions;if(!ok){++failures;std::cerr<<"FAIL line "<<line<<": "<<expr<<"\n";if(fatal)throw std::runtime_error(expr);}}
#define BOOST_AUTO_TEST_CASE(n) void n()
#define BOOST_REQUIRE_MESSAGE(x,m) do { if(!(x)){std::cerr<<(m)<<"\n";check(false,#x,__LINE__,true);}else check(true,#x,__LINE__); }while(0)
#define BOOST_REQUIRE(x) check(bool(x),#x,__LINE__,true)
#define BOOST_CHECK_MESSAGE(x,m) do {bool ok=bool(x); if(!ok)std::cerr<<(m)<<"\n"; check(ok,#x,__LINE__);}while(0)
#define BOOST_CHECK(x) check(bool(x),#x,__LINE__)
#define BOOST_CHECK_EQUAL(a,b) check((a)==(b),#a " == " #b,__LINE__)
std::vector<unsigned char> TinySafeTensors(unsigned char tag)
{
    const std::string json = "{\"__metadata__\":{\"t\":\"" + std::to_string(static_cast<int>(tag)) + "\"}}";
    std::vector<unsigned char> st(8 + json.size(), 0);
    WriteLE64(st.data(), json.size());
    std::memcpy(st.data() + 8, json.data(), json.size());
    return st;
}

fs::path WriteTinyModel(const fs::path& dir, unsigned char tag)
{
    fs::create_directories(dir);
    const auto st = TinySafeTensors(tag);
    std::ofstream out(dir / "model.safetensors", std::ios::binary);
    out.write(reinterpret_cast<const char*>(st.data()), static_cast<std::streamsize>(st.size()));
    return dir;
}

modelnet::CatalogEntry ImportTiny(modelnet::ModelCatalog& cat, const fs::path& dir, unsigned char tag, bool pin)
{
    std::string err;
    modelnet::CatalogEntry imported;
    BOOST_REQUIRE_MESSAGE(cat.ImportPath(fs::PathToString(WriteTinyModel(dir, tag)), pin, imported, err), err);
    return imported;
}

std::vector<unsigned char> ReadFileBytes(const fs::path& path)
{
    std::ifstream in(path, std::ios::binary);
    BOOST_REQUIRE_MESSAGE(in, fs::PathToString(path));
    return std::vector<unsigned char>((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
}


#include "maintained-cases.inc"
int main(int argc,char**argv){if(argc!=2)return 2;m_path_root=fs::path(argv[1]);if(fs::exists(m_path_root))return 3;fs::create_directories(m_path_root);
for(auto fn:{import_path_repairs_damaged_local_piece}){try{fn();}catch(const std::exception&e){std::cerr<<"CASE ABORT "<<e.what()<<"\n";}}
std::cout<<"ASSERTIONS="<<assertions<<" FAILURES="<<failures<<"\n";fs::remove_all(m_path_root);return failures?1:0;}
