// Calls unchanged production filesystem-jail wrapper and AppContainer backend.
#include <modelnet/swarm_fsjail.h>
#include <modelnet/swarm_native_io.h>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <vector>
namespace {
std::vector<unsigned char> Read(const fs::path& path)
{
    std::ifstream in(path,std::ios::binary);
    return {std::istreambuf_iterator<char>(in),std::istreambuf_iterator<char>()};
}
}
int wmain(int argc,wchar_t** argv)
{
    if(argc!=3)return 2;
    const fs::path worker=std::filesystem::absolute(argv[1]);
    const fs::path root=std::filesystem::absolute(argv[2]);
    fs::create_directories(root);
    const fs::path helper=root/L"tool.exe", input=root/L"input.bin";
    fs::copy_file(worker,helper,fs::copy_options::none);
    {std::ofstream out(input,std::ios::binary);out<<"finite-input\n";if(!out)return 3;}
    const auto before_helper=modelnet::native_io::Digest(Read(helper));
    const auto before_input=modelnet::native_io::Digest(Read(input));
    modelnet::SwarmFilesystemJailRequest request;
    request.root=root;request.helper=helper;request.network_denied=true;
    request.max_wall_seconds=3;
    // Existing Windows policy separately permits new output beyond the input cap.
    request.max_tree_bytes=fs::file_size(helper)+fs::file_size(input);
    std::string error;
    const auto result=modelnet::SwarmRunFilesystemJail(request,error);
    const auto output=Read(root/L"result.bin");
    const bool output_ok=output.size()==512 && std::all_of(output.begin(),output.end(),[](auto b){return b==0x42;});
    const bool inputs_ok=before_helper==modelnet::native_io::Digest(Read(helper)) &&
        before_input==modelnet::native_io::Digest(Read(input));
    const bool ok=result.launched && result.jailed && result.child_status==0 &&
        result.code=="JAILED" && error.empty() && output_ok && inputs_ok;
    std::cout<<"code="<<result.code<<" error="<<error<<" launched="<<result.launched
        <<" jailed_flag="<<result.jailed<<" child="<<result.child_status
        <<" input_cap="<<request.max_tree_bytes<<" output_bytes="<<output.size()
        <<" output_ok="<<output_ok<<" inputs_unchanged="<<inputs_ok<<" verdict="<<(ok?"PASS":"FAIL")<<'\n';
    return ok?0:1;
}
