# Native BTX historical funding-fee check for #806

**PASS at the native fee RPC boundary.** Current adopted Python reads **7,834 atoms** from an existing native BTX transaction; the separate wallet-fee oracle agrees. Wrong output returns `RECOVERY_CONFLICT`; an actually unavailable transaction returns `FUNDING_FEE_UNKNOWN`.

## Tested on

Mac ARM64, Python 3.12, production `UTXODriver.historical_funding_fee` and `LocalRPC` from `release-0.34.17` **bd847e2b986722c1723b4cd60988d4f4908452d4**. Saved native daemon source **949a98e34222cc4cdb5b1d5bd650aa3b7bcbff72**, executable SHA-256 **ac96c05d6a83a09dbb902f0d89fd04049897a0ac659660c228926a1ed31b9e6f**. This was not a new daemon build.

Relevant `src/rpc/rawtransaction.cpp` and `src/core_write.cpp` are byte-identical from saved949 to the prior3710 source, and unchanged from3710 tobd847. See source-provenance.json. This establishes compatibility of the selected RPC boundary, not identity of the complete current daemon.

One existing confirmed ordinary timelocked P2MR output (100,000 atoms) was checked on a disposable copy of a retained regtest chain/wallet. The actual production reader used verbosity-2 `getrawtransaction` with an explicit canonical block hint; its fee matched a separately obtained locally-sent wallet fee. Production does not use that wallet fee as authority.

- Correct transaction/output: **7,834 atoms**.
- Wrong expected script against that transaction: **RECOVERY_CONFLICT**.
- Actual unknown transaction lookup: **FUNDING_FEE_UNKNOWN**.
- Height remained105. No new funding, signing, broadcast or mining. Copied node stopped; original checkpoint unchanged.

## Evidence and execution

[result.json](result.json), [run.log](run.log), [run_native.py](run_native.py), [source-provenance.json](source-provenance.json), [independent review](REVIEW.md), and [MANIFEST.json](MANIFEST.json).

Executed with the bundled Python3.12 runtime as `python3 run_native.py` after checksum verification and isolated checkpoint preparation. The retained package/checkpoint and matching current Python tree are prerequisites; **this branch is an evidence/harness record, not a self-contained replay archive**. Wallets, cookies, keys, raw signed transaction bytes and chain databases are not published. Harness relative paths name the local retained fixture. Reconstruct an equivalent disposable known-payment fixture before adapting it; that reconstruction has not been executed from this branch.

One initial setup attempt compared a hexadecimal-text hash against the saved serialized-byte hash. It stopped before the fee query. Correcting it to hash decoded bytes produced the qualified run; this was a fixture correction, not a product fail-before/pass-after result. Independent review inspected the evidence and source; it did not execute a second native run.

## Not tested

Current native build or embedded coordinator, full SwapNet/HTLC settlement, refund replacement or signing, shielded funding, pruned/missing-undo history, Linux/Windows, or release qualification. The saved wallet-only regtest profile postpones MatMul activation and disables autoshielding; it does not qualify default consensus settings. Unknown-transaction refusal is not a pruned-undo test. Existing #806 component fee-cap, maturity, owner and retry/reopen results are reused, not rerun here.

No defect or product change was needed. This result complements Numair's adopted-code component run; it does not replace broader acceptance.
