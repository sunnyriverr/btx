#include <openssl/evp.h>
#include <openssl/crypto.h>
#include <openssl/ssl.h>
#include <stdio.h>
int main(void) {
    EVP_PKEY_CTX *kem = EVP_PKEY_CTX_new_from_name(NULL, "ML-KEM-768", NULL);
    EVP_PKEY_CTX *dsa = EVP_PKEY_CTX_new_from_name(NULL, "ML-DSA-44", NULL);
    SSL_CTX *tls = SSL_CTX_new(TLS_method());
    printf("headers=%s runtime=%s ML-KEM-768=%d ML-DSA-44=%d SSL_CTX=%d\n", OPENSSL_VERSION_TEXT, OpenSSL_version(OPENSSL_VERSION), kem != NULL, dsa != NULL, tls != NULL);
    const int ok = kem != NULL && dsa != NULL && tls != NULL;
    SSL_CTX_free(tls);
    EVP_PKEY_CTX_free(kem);
    EVP_PKEY_CTX_free(dsa);
    return ok ? 0 : 1;
}
