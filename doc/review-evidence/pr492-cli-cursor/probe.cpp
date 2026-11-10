#include <rpc/client.h>
#include <univalue.h>

#include <exception>
#include <iostream>
#include <string>
#include <vector>

int main(int argc, char** argv)
{
    if (argc != 5) return 2;
    const std::string method = argv[1];
    const std::string mode = argv[2];
    const std::string argument = argv[3];
    const std::string value = argv[4];
    try {
        std::vector<std::string> input;
        if (mode == "named") input.push_back(argument + "=" + value);
        else if (mode == "positional") input.push_back(value);
        else if (mode != "empty") return 2;
        const auto output = mode == "named" ? RPCConvertNamedValues(method, input) :
                                            RPCConvertValues(method, input);
        std::cout << output.write() << '\n';
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
