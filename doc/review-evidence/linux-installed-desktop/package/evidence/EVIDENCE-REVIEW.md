# Independent actual-evidence review — bounded Ubuntu acceptance

Disposition: PASS for the recorded exact-archive installed desktop and ordinary lifecycle acceptance on Ubuntu 24.04 x86_64 virtual X11. No material missing proof was found within this bounded acceptance scope. This review audits records and harness semantics; the parent session separately reviews the five screenshots visually. It does not confer official release qualification.

Reviewed read-only by delegated agent `desktop_native_evidence_review` in Session 3. No test/import, application execution, rebuild, download, CI dispatch or publication was performed by this reviewer. Only this report was written.

## Evidence identity and terminal state

- Run `44198893852`, job `134447512487`, attempt 1, control `6d719e9191cea74a2e5ba7081e6beb02d7fd38bd`. Local `run-terminal.json` and `job-terminal.json` both report completed/success; all listed job steps, including phase/evidence enforcement, succeeded. Job runner label is `ubuntu-24.04`; log verifies x86_64 and reviewed payload hashes before execution.
- `records14381370302.zip`: 708633 bytes, independently computed SHA256 `34645ac7a81a92a0c9ae1c595f66e948f1a7f89ed37d46f36377f479cc57bbff`. All 29 extracted record files were byte-compared with their ZIP entries: no differences. All five screenshot byte hashes match GUI result references.
- `acceptance-records/result.json` has overall PASS and exactly five PASS phases: artifact, installed_tree, gui, lifecycle, unchanged_payload. It reports no error, no cleanup signals, no remaining owned processes, unchanged payload and removed runtime. Thus disposition is supported by child results and explicit phase checks, beyond the workflow badge.

## Exact package admission and installation

Producer run `44063898937`, artifact `14319148652`, producer control `3145c20fe7f3c215a06398a052f573d5d5bf47aa`. Outer ZIP is pinned at 173356636 bytes / SHA256 `d9f58d9623a3e6d13b15b9e67ba2c2b16bb9b574985bbc9dcd69c4aed3daa664`. Inner `btx-linux-desktop-074-candidate.tar.gz` is pinned at 173082807 bytes / SHA256 `915fae283089a325df65ef7521fffd6e30f5faa8d0bc8f2d77a2b6af52348a57`. Preflight artifact metadata agrees and records the artifact unexpired. Controller admission checks exact sizes, both digests, four producer record digests, tar member set/types/modes/hashes, patch identity and installer digest; all precede artifact PASS. No rebuild occurred.

The four local pinned producer records were independently hashed against inputs.json and all match: members `3ac53ff76487b9ff25156e4a8b12b61e9d74f150804c319f2f522e5f2fe8e144`; provenance `1f81004e1062c4145970736b52ac0fcadacb335cb152dd94822443fcf934c13b`; package implementation `a836f4b4035442c76c8ad6936a4bee2293cad8aedb51315eee1fba61d1011982`; Python selection `0a189d23295d0bd5525f78ec1bfcec47f60562758b055877af06a1abe995be53`.

Installer manifest records prebuilt linux-x86_64, version label 0.34.16 and compiled source `074dac167c26c1e091198f691ed5727817dba88a`. Installer source SHA256 is `86799706f2824e5edcc541bb8a4301e03d99dd6538553d832418bdd08c473736`; packaging selector patch SHA256 `9ad1291bf4924465066c0f9ad11d06d823feaa6147a1f08a6c26859bc4795140`, candidate bundler SHA256 `721fa1f54b51223cde80a1c85c4b8c996da916c5dab2fd7ff4fc17a8be72eab7` (reviewed selector repair PR822). Installed_tree PASS requires copied bin/lib/libexec inventory equal to the admitted extracted package, except generated installer manifest. Independently compared all 802 recorded installed payload file hashes against the pinned member manifest: no mismatch. All 803 lifecycle before/after file hashes, including manifest, are identical. Controller and GUI additionally compare full file/mode/symlink inventories and recheck retained archive bytes.

Provenance explicitly retains compiled 074 checkpoint reuse. Atlas is reused from source `88c9b49cb16360fc8fbf3f84003b8b54c29e6db5`, equivalent Atlas tree `fc0957218a75f21f541077b76e953e80966595d9`, binary SHA256 `0c2757a32e2540be6a2ed4810a915430cdb1cb7018a0ede75d9f4256910fa13f`; it was not freshly compiled from 074 in this run. Producer/raw-CI 404 history is not repaired or erased by this new runtime result.

## GUI observations and ordinary exits

GUI result is PASS, wallet-disabled offline regtest. Recorded installed process identities are node PID 4408/start 31432, Qt PID 4833/start 31510 and Atlas PID 4944/start 31825, each from the run-specific installed/libexec tree. `owned-sessions.json` agrees with the result and records distinct owned sessions. Harness window lookup requires the exact installed executable and persisted PID/start identity, then matches window PID; launcher startup is waited for within the existing bound. Window close requires exactly one owned window and exit code zero.

Qt main-window check passed. Atlas launch, cookie picker, native confirmation and connected screenshot records exist with matching hashes. Native confirmation targets loopback `127.0.0.1:46161`, regtest, genesis `521ad0951ed299e9c56aeb7db8188972772067560351b8e55adf71dbed532360`, cross-checked against RPC. Both connected accessibility observations contain LIVE LOCAL, regtest, zero blocks and network inactive; times 348.342453846 and 353.425766099 are over five seconds apart. GUI normal_shutdown_pass requires ordinary owned window closes for Qt/Atlas and RPC stop with node exit code zero. GUI result reports package unchanged, no cleanup errors/signals/remnants and removed runtime. Node log ends with Shutdown: done.

Recorded host resolutions for libglib and libdbus point to declared Ubuntu host libraries. Virtual X11 EGL/DRI3 and portal/font warnings exist in logs; this result establishes successful observed windows and ordinary closes in that environment, not accelerated physical-desktop rendering.

## Two ordinary lifecycle boots

All 43 recorded lifecycle checks are true, including 20 health samples (0–9 for each boot), normal exits, clean boundaries, restart identity change and unchanged package bytes.

| Boot | Daemon PID/start | Direct-child helper PID/start | Direct-child guard PID/start |
| --- | --- | --- | --- |
| 1 | 5275 / 35478 | 5468 / 35504 | 5469 / 35504 |
| 2 | 9151 / 36370 | 9344 / 36396 | 9345 / 36396 |

Daemon/helper paths resolve to installed btxd.real/btx-modeld.real; guard resolves to installed btx-guardd. Helpers and guards have each boot daemon as PPID. Every health record is true, preserves the expected helper PID and guard identity/boot token, and records ready/valid-journal/zero automatic spend guard status. Reviewed harness semantics additionally require daemon-managed helper READY, zero helper restarts, fixed helper start ticks/executable/parent, regtest zero blocks and peers, no model peers, no advertised/public host, stable guard process start ticks and stable boot token. Samples are separated by 0.5-second waits; this is a short bounded observation, not a long soak.

Guard boot changes from `24dd0f1d4d6f6ebae8c447245567c571d53232d7a7dc54177f9aed4a8ef8cb95` to `7761684533b4b29bd554d7e85f27adfc4124b2ec5e4170e0d5558843fb76b840`. The full local publisher identity list survives restart unchanged. Offline helper arguments, no helper listener arguments, isolated 16 MiB storage and seed policy checks pass. No manual helper launch occurred. Both stop checks require RPC stop, daemon return code zero and no installed process after stop; logs finish with Shutdown: done. No fallback signals, remaining processes or retained disposable runtime are recorded in lifecycle or enclosing controller.

## Limits and retained history

Accept this as exact retained candidate acceptance: compiled 074 checkpoint plus explicit reviewed packaging selector patch, reused source88/tree-equivalent Atlas, one Ubuntu 24.04 x86_64 virtual X11 runner, disposable wallet-disabled offline regtest. It is not an official release or 0.34.17 qualification, fresh rebuild, physical desktop/Wayland or other-platform acceptance, wallet workflow, model retrieval/inference or SwapNet evidence. Guard status itself retains NOT_ESTABLISHED_BY_COMPONENT_SERVICE release scope and unproven model/general GPU safety flags.

The earlier three fixture failures remain historical failures with their original records; this successful readiness attempt does not relabel those results. Preserve producer/raw-CI 404 limitations as historical provenance/access evidence. Screenshot visual disposition belongs to the parent session; this report verifies their identity and corresponding machine observations only. No additional run is required by this review's bounded evidence findings.
