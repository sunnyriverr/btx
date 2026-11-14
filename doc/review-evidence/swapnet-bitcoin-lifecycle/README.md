# Tested Bitcoin preparation repair and native lifecycle evidence

Base f08e0b4be0eea06152ad83e47311ff8907f9c25d. Bitcoin repair0a8f3e98f06f5612717e6a2ed81b77a9553f9ba0; reused cleanup retry41ffb120a830ebc5302deb2c509dffbe117ef4b2 (originalbd24c36b). Combined binary source772b35d27a72a457f3995beea5597310a0b7a521.

Credit repch1c for the original Core32.1/watch-wallet/lifecycle reports and current all-direction live tests; Numair for the upstream recovery work. This handoff offers a tested repair and additional Linux evidence, not a competing claim of discovering his report.

## Bitcoin repair

Uses the supported positional PSBTv0 argument when wallet help advertises it, retaining older Core default behavior. Funding construction requests no locks; fee/input/output validation precedes explicit lock acquisition. Signing/store failures release only acquired inputs; pre-existing wallet locks survive. Store reservation follows signing validation.

Maintained tests: final164Pythonpass; combined15focusedpass. Same native Mac Core32.1 harness fails original fee-lock invariant and passes candidate; native30.4passes; mixed locked/unlocked input batches reject atomically in both orders. See paired_native.py (run with candidate contrib/swapnet and tests on PYTHONPATH, CASE_DIR fresh), raw receipts and repair-evidence-index.json. Official Core32HTTPS checksum verified; PGP signature not independently checked. Old raw Core32scope description incorrectly says30.4; binary hash/version pins32.1 and the correction is retained in the index. Lost RPC responses/process death are not made crash-atomic by this repair.

## Native combined candidate

Build43573514061 passed; binary bundle SHA2569370cbdbdfa6ff4317168fc702906448028938345b248a3e9decf85ad287faf5, all257payload hashes verified. Resumable objects retained in the same run. Native unfunded discovery43575477253 passed mutual admission, signed provider sequence2→3 after restart, disable/defaultoff and zero sessions. Native funded43576084156 passed BTX→BTC settlement after first-funding restart, exact chain/wallet reconciliation, and a separate mature refund/reopen. Detailed reports and digest receipts included.

Limits: Ubuntu24.04/Core30.4 for full lifecycle, ModelNetOFF and toy regtest MatMul activation flags; Mac32.1/30.4 preparation tests have simulated BTX counterleg. Linux settlement fixture submitted canonical Bitcoin blocks141–160 after peer relay lag; not an automatic relay pass. Reverse/nativeCore32full settlement/ETH/package/release acceptance not claimed. No new accounting fault or Bitcoin outage injected in the final lifecycle run. Prior scoped fault evidence remains separate.

Discovery's inherited finalizer mistakenly writes raw stage=settlement verified; it performed no settlement. Explicit controls, report and correction govern that verdict. Initial unsynchronized-chain discovery pilot is retained locally; corrected readiness used3test blocks. No product change arose from that setup error.

## Current contributor coverage

repch1c now reports all four live directions and refunds on f08 plus a one-line PSBT workaround, at https://github.com/btxchain/btx/pull/630#issuecomment-6874643101 . Reuse that native coverage; do not start a duplicate reverse-direction campaign. This repair also addresses failed-preparation locks; independent maintainer review/adoption remains pending.

Run links: https://github.com/sunnyriverr/btx/actions/runs/43573514061 ; https://github.com/sunnyriverr/btx/actions/runs/43575477253 ; https://github.com/sunnyriverr/btx/actions/runs/43576084156 .
