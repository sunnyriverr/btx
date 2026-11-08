#include <modelnet/proc08/proc08.h>
#include <util/fs.h>
#include <algorithm>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>

static std::string Forward(std::string s) { std::replace(s.begin(), s.end(), '\\', '/'); return s; }
static void Run(const char* label, const std::string& path, const std::string& root)
{
    modelnet::Proc08 engine;
    std::string err="stale";
    const bool accepted=engine.AcceptResearchPath(path, root, err);
    std::cout << "{\"case\":" << std::quoted(label) << ",\"path\":" << std::quoted(path)
              << ",\"root\":" << std::quoted(root) << ",\"accepted\":" << (accepted?"true":"false")
              << ",\"error\":" << std::quoted(err) << ",\"research_outside\":" << (engine.research_outside()?"true":"false")
              << ",\"release_qualified\":" << (engine.release_qualified()?"true":"false")
              << ",\"gpu_passed\":" << (engine.gpu_passed()?"true":"false")
              << ",\"windows_passed\":" << (engine.windows_passed()?"true":"false") << "}\n";
}
int main(int argc, char** argv)
{
    if (argc!=2) return 2;
    const fs::path base=fs::PathFromString(argv[1]);
    const fs::path root=base/"proc08-evidence", file=root/"a.txt", nested=root/"sub";
    const fs::path outside=base/"proc08-outside", prefix=base/"proc08-evidence-other";
    fs::create_directories(root);fs::create_directories(nested);fs::create_directories(outside);fs::create_directories(prefix);
    { std::ofstream out{file,std::ios::binary};out<<"alpha";if(!out)return 3; }
    const std::string r=fs::PathToString(root), f=fs::PathToString(file), mixed=r+"/a.txt";
    std::cout << "{\"same_file_mixed\":" << (fs::equivalent(file,fs::PathFromString(mixed))?"true":"false")
              << ",\"same_file_forward\":" << (fs::equivalent(file,fs::PathFromString(Forward(f)))?"true":"false") << "}\n";
    Run("root_self",r,r);
    Run("inside_file_native",f,r);
    Run("inside_file_mixed",mixed,r);
    Run("inside_file_forward",Forward(f),Forward(r));
    Run("inside_dir_native",fs::PathToString(nested),r);
    Run("inside_dir_mixed",r+"/sub",r);
    Run("inside_missing_native",fs::PathToString(root/"absent"),r);
    Run("inside_missing_forward",r+"/absent",r);
    Run("outside_native",fs::PathToString(outside),r);
    Run("outside_forward",Forward(fs::PathToString(outside)),Forward(r));
    Run("prefix_sibling_native",fs::PathToString(prefix),r);
    Run("prefix_sibling_forward",Forward(fs::PathToString(prefix)),Forward(r));
    Run("missing_outside",fs::PathToString(base/"absentoutside"),r);
    Run("empty","",r);
    return 0;
}
