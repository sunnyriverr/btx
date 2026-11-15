#include <filesystem>
#include <fstream>
#include <iostream>
int main(){namespace fs=std::filesystem;fs::path root="records/cleanup-fixture";fs::create_directories(root);{std::ofstream out(root/"file");out<<"retained";}std::ifstream in(root/"file");std::string bytes;in>>bytes;if(bytes!="retained")return 1;std::error_code ec;fs::remove_all(root,ec);if(!ec)return 2;in.close();fs::remove_all(root,ec);if(ec||fs::exists(root))return 3;std::cout<<"Open-stream refusal reproduced; closing stream permits complete cleanup PASS\n";}
