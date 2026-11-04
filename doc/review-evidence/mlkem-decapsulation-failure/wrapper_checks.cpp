#include <crypto/ml_kem.h>
#include <util/translation.h>
#include <array>
#include <iostream>
#include <optional>
#include <string>
const TranslateFn G_TRANSLATION_FUN{nullptr};
int main(int argc, char** argv)
{
    if (argc != 2) return 2;
    std::array<uint8_t, mlkem::KEYGEN_SEEDBYTES> seed{};
    seed.fill(0x42);
    const auto kp = mlkem::KeyGenDerand(seed);
    std::array<uint8_t, mlkem::ENCAPS_SEEDBYTES> coins{};
    coins.fill(0x24);
    const auto enc = mlkem::EncapsDerand(kp.pk, coins);
    auto sk = kp.sk;
    auto ct = enc.ct;
    const std::string mode{argv[1]};
    bool rejection = false;
    if (mode == "empty") sk.clear();
    else if (mode == "short") sk.resize(mlkem::SECRETKEYBYTES - 1);
    else if (mode == "long") sk.resize(mlkem::SECRETKEYBYTES + 1);
    else if (mode == "wrong") { seed.fill(0x43); sk = mlkem::KeyGenDerand(seed).sk; rejection = true; }
    else if (mode == "altered") { ct[0] ^= 1; rejection = true; }
    else if (mode != "valid") return 2;
    const std::optional<mlkem::SharedSecret> ss = mlkem::Decaps(ct, sk);
    const bool invalid = mode == "empty" || mode == "short" || mode == "long";
    const bool pass = invalid ? !ss : (ss && ss->size() == mlkem::SHAREDSECRETBYTES && ((*ss == enc.ss) != rejection));
    if (!pass) return 1;
    std::cout << mode << ": PASS\n";
    return 0;
}
