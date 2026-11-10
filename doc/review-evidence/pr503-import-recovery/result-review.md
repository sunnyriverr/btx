# Internal result review — run 42921100457

The retained evidence supports a scoped recovery defect on exact author #503: the first catalog-save failure is reported truthfully and preserves the old catalog, but an identical same-process retry acknowledges B as PINNED without making B durable. After clean restart B is absent from live/catalog state, ordinary re-import fails because its artifact exists, and export by B's model ID returns NOT_FOUND. B's stored payload bytes remain intact. This is a completed experiment with failed recovery acceptance, not a fixture/control failure or a product pass.

Internal review of retained evidence, not an external contributor reproduction or another platform run.

## Provenance and integrity

- CI run: 42921100457, completed/success, fixture/controller commit `12763af1bbf4b1877bfeb1e01e61f3805f33d63f`, branch codex/ci-model-import-recovery.
- Product: `08fd0a6245598e8f9fedc6dac97629310335dd2d`, tree `1fa445dd7b06901baf7888b97e6dbf79ac02ef0e`, base `dac9aee53520bd49ed320ec7a49b9072fc7d88d9`.
- Candidate binary: `2752a364a568d7032743c7020c2f9b621db97df32dbb5cffc81d6aecbda128dd`. Build receipt and both native journey records agree. The fixture independently hashes the binary and checks each launched /proc/<pid>/exe.
- Executed fixture digest: `fcfb2d3c0b963fd11880b588552ac7eb76bc814a8e0a36e4a985d7c65e7dde71`, matching the current retained native_fixture.py bytes and summary.json.
- Restored checkpoint digest: `90391b49487f57e3c820200f28142e6873b0fecbb2a2d4b82091e48050437176`; full restoration verified, original archive unchanged. Author/candidate clean logs are empty; exact six-file delta, blobs and tree are retained. Untracked count is zero. The actual compile log contains the admitted thirteen actions and completes in 900.73 seconds; no broad rebuild is shown.

Separately recomputed every collected file digest: all 27 build-record files and all seven native-record files match their collection receipts. Build artifact 13812877487 has collection/archive digest `6c169503b3de242f04b8c44b85907104df1b855194f2682b726b1a2d7092d671`; native artifact 13811694339 has digest `93ea579848b1320f203346c564267bb1f1dc087811962a6c7d3c134588b5e8d3`. Both receipts bind the run/controller above. These archive digests are the collector's verified-download receipts; the independently repeated check here covers the extracted files, not another archive download.

## Actual controls and primary observations

Healthy acceptance is true with no failed conditions. A and B are durable before stop and remain exactly the two live/disk entries after clean restart. Ordinary B re-import succeeds with the expected IDs. Both direct piece checks and exports match exact input bytes. The full original A disk row remains unchanged. This legitimate control completed and cleaned up before the fault journey began.

In the fault journey, import B request id 5 returns `IMPORT_FAILED`, message `catalog write failed`. The obstruction is then removed. Request id 7 repeats the identical method, source path and {pin:true,publish:false} options and returns success, admission PINNED, pinned=true, with the same model/artifact IDs as the healthy B. Request id 11 after restart again uses the same method/params and fails `IMPORT_FAILED: destination artifact exists`.

The catalog hash is **`1957db0bc87418c858c7569694058f02654d17015da900ccfd8c56711840a19e`** from the initial A-only state through failed B import, acknowledged retry, two-second grace, clean shutdown, restart and failed post-restart re-import. Every before/after-list hash matches and every list_changed_catalog is false. shutdown_changed_catalog and restart_changed_catalog are false. Thus neither the observed listmodels calls, measured grace interval, ordinary shutdown nor restart healed this catalog state.

Before stop, live listing contains A and B while disk contains only A. After restart, both the actual live rows and disk rows contain only A; B specifically is absent, so the lost-acknowledged-import shorthand is supported by the rows rather than merely a two-entry count mismatch. A's complete persisted row equals the original A row. Its committed piece and exported file both match the original input after the fault/restart sequence.

## Artifact-before-save proof and byte-loss distinction

B artifact ID is `5513b0b29ed585e81d4df7ebf6a855b50eec265de3f1077d5ada051f834d3ff48565166ce04a742838ea5ed55b4b9e82`; B model ID is `9756df0a998b0a885294830e39f711d884f83455d93611d49345ac1149b86a28e50e9e0ebac1c2dfb4402d0f90ffeea5`.

In snapshots.after_first_b.artifacts[B artifact]["0/0.piece"], recorded **35-byte** payload SHA-256 is **`d5f6e549fa5f83e35b7a8aa0e459009ab37006013ae15debc2b6209081a1cd9c`**, exactly equal to input_sha256.b and the healthy input. This snapshot precedes removal of the catalog obstruction and the retry. It establishes the expected payload existed at its final artifact path when the first catalog save had failed; the conclusion does not rely on directory presence alone.

Later direct B piece equality is still true. B export returns code NOT_FOUND with null result, whereas A export succeeds and matches. Therefore both_model_bytes_usable=false denotes B's catalog-dependent unavailability through export, **not missing or corrupted B payload**. The evidence demonstrates retained/orphaned committed bytes plus lost catalog reachability. It does not qualify fsync/power-loss durability of those bytes.

## Completion, cleanup and claim boundaries

summary.json reports experiment_complete=true and recovery_acceptance_pass=false. Fault failed conditions are immediate retry durability, two-entry live/disk restart state, post-restart import success/expected return, and combined usability. Both journeys report clean_shutdown=true, owned_runtime_removed=true, empty cleanup_signals, and no experiment_error or cleanup_error. Fixture clean-stop success entails helper exit zero and removal of its Unix socket. No forced termination manufactured the restart result.

Required claim corrections/limits:

1. A green CI conclusion means completed characterization; it does not mean #503 passed recovery acceptance.
2. Say the **retry** falsely acknowledged an undurable import; the initial save failure was correctly reported and old catalog bytes were preserved.
3. Say B disappeared from catalog/live listing after restart and normal re-import/export were blocked; do not say B's bytes were lost or corrupted, or A was lost.
4. This is a nonempty catalog-temp-directory/open-failure experiment, not a native disk-full/late-close/short-write result.
5. Only the exact #503 candidate ran this fixture. The stock helper was retained but not executed, so there is no stock-versus-#503 regression or fix comparison and no evidence that #503 introduced the underlying recovery issue.
6. Linux helper Unix RPC, tiny maintained safetensors-shaped inputs, no inference/network/user model execution. No Windows/macOS, all-store transactionality, machine-crash recovery or repair qualification is established.

No material inconsistency found between actual evidence and the scoped result above. The evidence is sufficient for the owner to resolve the supported import-retry recovery decision without another reproduction run.
