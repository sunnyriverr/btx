# #470 Windows label export verification

The real exportlabels RPC reproduced false success on dac9aee5 and passed with
repch1c's labels.cpp hunk from a369752d. The same harness ran both binaries on
Windows Server 2025 x64 with clang-cl 20.1.8 and MSVC 14.51 libraries. It used
disposable zero-funds regtest wallets and a capped 64 MiB FAT virtual disk.

| Check | Stock dac9aee5 | With #470's product hunk |
| --- | --- | --- |
| Healthy export | Eight valid labels in 952 bytes | Byte-identical export |
| Existing destination | Error -8, bytes preserved | Error -8, bytes preserved |
| Zero free bytes | Reports eight labels, leaves a zero-byte file | Error -4, no partial file |
| Same-path retry after space is restored | Passes after removing the zero-byte file | Passes without manual cleanup |

Both retries produced the same complete JSONL as the healthy exports. Both nodes
shut down cleanly, their disposable wallets were removed and the test VHD was
detached and deleted.

The verified checkpoint restored 12,858 files. Eight build actions relinked
the exact author hunk with its expected generated dependencies. The native
workflow and artifact contain the executed entry point, source checks and logs.

[Executed Windows run](https://github.com/sunnyriverr/btx/actions/runs/42811666496) ·
[Exact CI fixture](https://github.com/sunnyriverr/btx/tree/ffd25d2cf7e6a29e7b5afc9ca33200e66756cda8) ·
[Source and binary identities](provenance.json) · [Matched observations](wallet-results.json).

Scope is one matched native Windows Server/FAT comparison using the product
hunk. Windows 11, NTFS and full-suite testing remain outside this scope.

Credit to repch1c for the patch and original Mac reproducer.
