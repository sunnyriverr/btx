// Disposable signed-channel fixture; no wallet, persisted private key or network calls.
#include <bitcoin-build-config.h>
#include <modelnet/identity.h>
#include <modelnet/model_watch.h>
#include <modelnet/resource_uri.h>
#include <support/cleanse.h>
#include <util/strencodings.h>
#include <iostream>
#include <stdexcept>
using namespace modelnet;
int main()
{
    std::vector<unsigned char> pk, sk;
    std::string err;
    if (!GenerateMlDsa44(pk, sk, err)) { std::cerr << err << '\n'; return 1; }
    UniValue output(UniValue::VOBJ);
    for (const auto& name : {"unrelated", "target"}) {
        for (uint64_t seq = 1; seq <= 2; ++seq) {
            Digest48 model{}; model.data[0] = name[0] == 'u' ? 0x61 : 0x71;
            model.data[1] = seq;
            SignedChannel channel;
            channel.pubkey = pk; channel.name = name; channel.channel = "stable";
            channel.sequence = seq; channel.expiry = 0;
            if (!EncodeResource(ResourceKind::MODEL, model, channel.target_uri, err) ||
                !SignSignedChannel(channel, Span<const unsigned char>{sk.data(), sk.size()}, err) ||
                !VerifySignedChannel(channel, 1, err)) {
                memory_cleanse(sk.data(), sk.size()); std::cerr << err << '\n'; return 1;
            }
            UniValue row = SignedChannelToJson(channel);
            row.pushKV("pubkey", HexStr(pk)); row.pushKV("signature", HexStr(channel.sig));
            output.pushKV(std::string(name) + "_" + std::to_string(seq), row);
        }
    }
    memory_cleanse(sk.data(), sk.size());
    std::cout << output.write(2) << '\n';
    return 0;
}
