// Bounded probe of the unmodified real S3 transport; disposable local origin only.
#include <bitcoin-build-config.h>
#include <modelnet/s3_client.h>
#include <util/translation.h>
#include <algorithm>
#include <iostream>
#include <sstream>
#include <stdexcept>
const TranslateFn G_TRANSLATION_FUN{nullptr};
int main(int argc, char** argv)
{
    try {
        if (argc != 6) throw std::runtime_error("expected endpoint key bytes known|unknown attempts");
        const uint64_t size = std::stoull(argv[3]);
        const auto attempts = std::stoul(argv[5]);
        if (size > (20U << 20) || !attempts || attempts > 2) throw std::runtime_error("probe bounds");
        modelnet::S3ClientConfig cfg;
        cfg.endpoint = argv[1]; cfg.bucket = "completion-probe";
        cfg.use_fake = false; cfg.allow_http_loopback = true;
        cfg.creds = {modelnet::CredentialRefKind::ENV, "BTX_COMPLETION_CREDENTIALS"};
        modelnet::S3Client client; std::string err;
        if (!client.Init(cfg, err)) throw std::runtime_error("Init: " + err);
        if (client.UsesFake()) throw std::runtime_error("unexpected FakeS3");
        std::string payload(size, '\0');
        for (size_t i = 0; i < payload.size(); ++i) payload[i] = static_cast<char>((i * 17 + 3) % 251);
        UniValue out(UniValue::VOBJ), rows(UniValue::VARR);
        out.pushKV("fake", client.UsesFake()); out.pushKV("length", size);
        out.pushKV("payload_sha256", modelnet::Sha256Hex(Span<const unsigned char>{reinterpret_cast<const unsigned char*>(payload.data()), payload.size()}));
        for (unsigned attempt = 0; attempt < attempts; ++attempt) {
            std::istringstream input(payload); err.clear();
            const bool ok = client.PutStream(argv[2], input, std::string(argv[4]) == "known" ? size : 0, err);
            UniValue row(UniValue::VOBJ); row.pushKV("upload_ok", ok); row.pushKV("upload_error", err);
            row.pushKV("health_after_upload", client.HealthJson());
            row.pushKV("max_buffer", static_cast<uint64_t>(client.LastPutMaxBufferBytes()));
            uint64_t observed = 0; std::string headerr;
            const bool head = client.Head(argv[2], observed, headerr);
            row.pushKV("head_ok", head); row.pushKV("head_size", observed); row.pushKV("head_error", headerr);
            std::vector<unsigned char> got; std::string geterr;
            const bool get = client.Get(argv[2], got, geterr);
            row.pushKV("get_ok", get); row.pushKV("get_error", geterr);
            row.pushKV("bytes_match", get && got.size() == payload.size() && std::equal(got.begin(), got.end(), reinterpret_cast<const unsigned char*>(payload.data())));
            rows.push_back(row);
        }
        out.pushKV("attempts", rows); std::cout << out.write(2) << '\n'; return 0;
    } catch (const std::exception& ex) { std::cerr << ex.what() << '\n'; return 1; }
}
