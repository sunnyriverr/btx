# v0.34.16 published download observation

Following Jpp-matata’s signed-checksum request on btxchain/btx#432, observation completed15Nov2026 08:09UTC. CPU asset750020860:97,001,150bytes/SHA256807d033d224979f086203e0ccfdcee2a0a97d8f381c8e9144a481c5347014087. CUDA asset750020823:452,206,209bytes/SHA25618c860c02e3a3f79851dc7caabcdc5dfc756fd062b4d077180c45776dc0472a7. Both match the downloaded SHA256SUMS and GitHub digests; checksum file’s digest matches metadata too. Asset identity/size/digest/update times remained stable across downloads.

The release notes/tag map to074dac167c26c1e091198f691ed5727817dba88a; tag snapshots retained. Passive inventories have856CPU/846CUDA members, btx-0.34.16 root, no Qt/Atlas; CUDA includes libcublasLt.so.13. No source-to-binary attestation was established from inventory. External build evidence was not assessed; no reproducible build was performed.

The release explicitly says its checksums are unsigned and lists no SHA256SUMS.asc. No trusted official fingerprint or signature verified. These results establish byte consistency with the publication, not independently authenticated publisher identity or binary build source. A signature checked against a separately trusted release identity would authenticate the checksum statement, not independently prove reproducible compilation.

Actual execution: macOS arm64/Python3.9.6, one bounded-memory HTTPS/tar pass per archive; all compressed response bytes hashed, including remaining bytes after tar iteration. No archive saved or content executed. No binary version command, installer, node, wallet, native test, GPU, seed, key or hosted job.

Evidence: machine receipt, exact checksum, before/after public release snapshots, tag mapping and header inventories. source-reuse.json compares the16 earlier signing-review files:14 unchanged onmain074,2 changed; this is applicability only, not a new test result. Earlier55+3 signing/recovery checks used simulatedGPG/API at a5d1637f, not these releases’ real signatures.

verify_downloads.py is the executed hashing/tar recipe adapted only to replace the local authenticated API helper with public unauthenticated GETs. The portable version was not rerun; the original executed recipe’s hash is in manifest.json. It downloads large archives if run. This is evidence tooling, not a new product patch or release gate.
