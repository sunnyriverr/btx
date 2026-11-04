#include <crypto/ml_kem.h>
#include <shielded/bundle.h>
#include <shielded/note.h>
#include <shielded/note_encryption.h>
#include <util/translation.h>
#include <iostream>
#include <vector>
const TranslateFn G_TRANSLATION_FUN{nullptr};
int main()
{
    const auto kp = mlkem::KeyGen();
    const std::vector<uint8_t> view(32, 0x42), aad{'m','e','t','a'};
    const auto grant = CViewGrant::Create(view, kp.pk);
    const auto bound = CViewGrant::CreateWithAad(view, kp.pk, aad);
    ShieldedNote note;
    note.value = COIN;
    note.recipient_pk_hash = uint256::ONE;
    note.rho = uint256::ONE;
    note.rcm = uint256::ONE;
    const auto enc = shielded::NoteEncryption::Encrypt(note, kp.pk);
    int checks = 0, failures = 0;
    for (const size_t n : {size_t{0}, mlkem::SECRETKEYBYTES - 1, mlkem::SECRETKEYBYTES + 1}) {
        auto sk = kp.sk; sk.resize(n);
        failures += grant.Decrypt(sk).has_value();
        failures += bound.DecryptWithAad(sk, aad).has_value();
        failures += shielded::NoteEncryption::TryDecrypt(enc, kp.pk, sk).has_value();
        checks += 3;
    }
    const auto a = grant.Decrypt(kp.sk), b = bound.DecryptWithAad(kp.sk, aad);
    const auto c = shielded::NoteEncryption::TryDecrypt(enc, kp.pk, kp.sk);
    if (!a || !b || !c || !std::equal(a->begin(), a->end(), view.begin(), view.end()) || !std::equal(b->begin(), b->end(), view.begin(), view.end()) || c->value != note.value) return 1;
    std::cout << checks + 3 << " caller checks, " << failures << " failures\n";
    return failures ? 1 : 0;
}
