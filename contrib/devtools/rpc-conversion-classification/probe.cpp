#include <vector>
#include <rpc/client.h>
#include <iostream>
#include <string>
int main() {
    std::string line;
    while (std::getline(std::cin, line)) {
        UniValue spec;
        if (!spec.read(line)) return 2;
        const auto method = spec[0].get_str();
        const auto idx = spec[1].getInt<int>();
        const auto name = spec[2].get_str();
        const auto value = spec[3].get_str();
        UniValue out(UniValue::VARR);
        for (int named = 0; named < 2; ++named) {
            UniValue rec(UniValue::VOBJ);
            try {
                UniValue v;
                if (named) v = RPCConvertNamedValues(method, {name + "=" + value})[name];
                else {
                    std::vector<std::string> args(idx + 1, "null");
                    args[idx] = value;
                    v = RPCConvertValues(method, args)[idx];
                }
                rec.pushKV("value", v);
                rec.pushKV("type", int(v.getType()));
            } catch (const std::exception& e) { rec.pushKV("error", e.what()); }
            out.push_back(rec);
        }
        std::cout << out.write() << "\n";
    }
}
