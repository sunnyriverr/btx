#include <crypto/ml_kem.h>
#include <util/translation.h>
#include <algorithm>
#include <array>
#include <iostream>
const TranslateFn G_TRANSLATION_FUN{nullptr};
int main()
{
    int checks = 0;
    std::array<uint8_t, mlkem::KEYGEN_SEEDBYTES> seed{};
    for (const uint8_t value : {uint8_t{0}, uint8_t{0x42}, uint8_t{0xff}}) {
        seed.fill(value);
        const auto kp = mlkem::KeyGenDerand(seed);
        if (!mlkem::IsValidEncapsulationKey(kp.pk)) return 1;
        const auto enc = mlkem::Encaps(kp.pk);
        if (mlkem::Decaps(enc.ct, kp.sk) != enc.ss) return 1;
        checks += 2;
    }
    mlkem::PublicKey pk{};
    if (!mlkem::IsValidEncapsulationKey(pk)) return 1;
    std::fill(pk.end() - 32, pk.end(), uint8_t{0xff});
    if (!mlkem::IsValidEncapsulationKey(pk)) return 1;
    pk.fill(0xff);
    if (mlkem::IsValidEncapsulationKey(pk)) return 1;
    for (size_t offset = 0; offset < mlkem::PUBLICKEYBYTES - 32; offset += 3) {
        for (const uint16_t value : {uint16_t{0}, uint16_t{3328}, uint16_t{3329}, uint16_t{4095}}) {
            for (const bool second : {false, true}) {
                mlkem::PublicKey sample{};
                const uint16_t a = second ? 0 : value, b = second ? value : 0;
                sample[offset] = a & 0xff;
                sample[offset + 1] = (a >> 8) | ((b & 0x0f) << 4);
                sample[offset + 2] = b >> 4;
                if (mlkem::IsValidEncapsulationKey(sample) != (value < 3329)) return 1;
            }
        }
    }
    std::cout << "Local encoding range/position, generated-key agreement and seed controls PASS\n";
    return 0;
}
