# PR473 Linux helper save and restart review

**Scoped Tested ACK 07c588fe for pledgemodelrelease save-error, retry and clean restart.** Repch1c owns the atomic-file, caller staging and snapshot-lock fixes. This branch retains their exact product tree and adds this evidence directory.

## Executed inputs and entry point

- Product head `07c588fe22545dff59a4744701ae9e01c7854cf9`, tree `4d445f29749c6e795c09b555c763c7585725d9e8`, on release `dac9aee53520bd49ed320ec7a49b9072fc7d88d9`.
- [Actual job 42916052312](https://github.com/sunnyriverr/btx/actions/runs/42916052312), fixture `85b122b61250aa921294478ac4b09ae3fd8f22d9`. The workflow and exact executed Python wrappers are in recipe/. The native step executed `python3 qualification/run_updated.py` after placing the verified helper and build receipt in the workflow's input directories.
- Ubuntu 22.04 x86_64, GCC 11.4.0, OpenSSL 3.5.9. Candidate helper SHA-256 `4f8b9a145819fde0b7849a00fd5911fe1130df23440a2f9012a99eaa73ed8693`. The restored checkpoint, original archive and complete tracked source were verified. Nine admitted compilation/link actions rebuilt the helper target. The maintained unit-test object was not compiled or run in this qualification.
- The workflow uses immutable retained artifacts from build42787985840. Those hosted inputs expire on 24 November UTC. This is the executed retained-cache recipe, not a claim of a fresh full build. The successor checkpoint remains retained remotely and has not been restored. Qualification is reproducible from the pinned source with equivalent dependencies, but that separate clean reconstruction has not been executed here.

## Observations

The disposable helper hosts a tiny generated SafeTensors file and creates a local campaign with one pledged atom. No wallet or payment is involved.

The helper's process file limit is set to the prior campaigns.json length, 8,633 bytes, with SIGXFSZ ignored. strace records a partial write to campaigns.json.tmp followed by EFBIG. The real Unix RPC returns result:null and INTERNAL with 'cannot save campaigns.json; pledge not recorded'. Live pledge and old file bytes/hash remain unchanged. The limit stays active until the helper exits normally.

A fresh helper with healthy limits loads one atom. A getreleasefeed persistence pass and another restart still leave one atom. Retrying the identical 10,000,000-atom pledge once produces 10,000,001 in memory and on disk, and a final clean restart retains that exact amount. Readiness, normal seed/save/restart and temporary-file cleanup controls pass. Every process exits normally and all isolated runtime directories are removed.

Inspect [native results](native/result.json), the [campaign syscall trace](native/candidate-campaign-io.log), [build results](build/result.json) and [qualification identities](qualification.json). The result wrapper passed 19 offline negative controls before native execution. The manifest records the exact bytes of every evidence file.

## Baseline reuse and limits

[Earlier Linux evidence](https://github.com/sunnyriverr/btx/tree/c5763b436cf79a455db3495aa049fe480cfe70ad/doc/review-evidence/pr473-campaign-persistence) pins the real-helper first-commit baseline at 15b337e2. That helper acknowledged the failed increment, retained it only in memory and lost it at restart. The new job reused that observation and ran the updated candidate only. The final wrapper adds shared feed persistence and same-request retry controls, so the complete final harness was not executed against the older binary.

Scope is one process-level candidate sequence via Unix RPC with a file-size fault. Physical disk exhaustion, btxd HTTP proxy, the full suite, Windows/macOS, funding/spending, peers and inference were outside this run. Repch1c's four-caller and concurrent-writer component results remain his macOS evidence. Transport loss after a possible commit still has an unknown outcome and does not gain automatic retry safety.

Collection initially put two result.json files in one local directory. The collector was corrected to separate artifacts, and both immutable archives plus every extracted member were reverified. This caused no native rerun. The published directories use the verified separated layout.
