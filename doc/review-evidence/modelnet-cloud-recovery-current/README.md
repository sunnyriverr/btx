# Current Linux ModelNet recovery qualification

**Tested helper at f40eb37a: missing-piece/partial/corrected-origin recovery and restart pass; quota-blocked state survives restart and completes with zero new origin GETs.**

Start with [REPORT.md](REPORT.md) and [operator guidance](OPERATOR-RECOVERY.md). The current helper SHA256 is `41c07b549f2c1b1abfa259345267757c52d7ba7e3bf501cb6b0e68a8d6a87bb6`.

- [Build](https://github.com/sunnyriverr/btx/actions/runs/43654513467): [verified source/binary receipt](build/verified-build.json), [native build record](build/records/records/build-result.json).
- [Primary native run](https://github.com/sunnyriverr/btx/actions/runs/43655225026): [receipt](primary/qualification-receipt.json), [results and actual exits](primary/results).
- [Extra quota restart run](https://github.com/sunnyriverr/btx/actions/runs/43655466244): [receipt](quota-restart/qualification-receipt.json), [result/exit/log](quota-restart/results).
- Earlier catalog-deletion/reimport result, distinct retained-helper profile: [original immutable evidence](https://github.com/sunnyriverr/btx/tree/24914510fefbb2864f7e2157170676fb2b2bce66/doc/review-evidence/modelnet-catalog-recovery).

Runtime was Ubuntu24.04 x86-64, real pinned MinIO PIECE_OBJECTS, small one-file fixtures, current helper with older8d6RPC proxy. No FakeS3 fallback. Exact source/toolchain/cache/artifact identities and limits are in the receipts. This does not qualify a whole current daemon/installed package, other platforms/layouts/scaling or a release.

Each stage includes its executed workflow/runner/driver inputs. These are records/reconstruction recipes; the documentation directory itself was not independently executed. Artifact availability is time-bounded in the saved metadata. Full layout matrix and earlier fail-before controls were not repeated just for current integration.

Credits: repch1c's real-MinIO fixture/quota work, reused source authors, and Numair's integration/component reports. The cloud-only metadata restore contract remains the separate question on613; no new restore mechanism is supplied. [SHA256SUMS](SHA256SUMS) pins the included files.
