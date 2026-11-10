# Current Linux desktop candidate: acceptance evidence

**PASS on Ubuntu 24.04 x86_64 virtual X11:** the reconstructed candidate passes archive admission, renders Qt and Atlas, connects Atlas through its native picker, and separately restarts node-owned helper/guard services cleanly.

This addresses the desktop usability gap reported by Jpp-matata on #432. It is not a replacement official release or a clean full producer rebuild.

## Exact inputs and outcome

| Item | Identity |
| --- | --- |
| Accepted source | release-0.34.16 `dac9aee53520bd49ed320ec7a49b9072fc7d88d9` |
| Official input archive | `0552bcbceef9fab5a6b9e24f26f4ccf7e615437e5d4c4af608a6247d5c21e6dc` |
| Candidate archive | `0caaa7d2d762d51bde262bff0bfb3965f58cc09bb1726b034783608930d3d633` |
| Qt producer binary | `7239c3b1e80e8114e47ebf3bd5b060b95c23db746dd70533681a9858763329a5` |
| Atlas producer binary | `720a718afbe1d8e282345057acc7ff22af5121de1f004b57f644565cbb0ad8be` |

Qt was rebuilt from dac9 using the verified Ubuntu22/GCC11.4/Qt6.2.4/static OpenSSL3.5.9 checkpoint, two workers, 643.24s. Its binary needs GLIBC2.34/GLIBCXX3.4.30/CXXABI1.3.13; all67 builder-resolved images stay within2.38. The uploaded successor checkpoint was independently restored and matched to the separately uploaded binary. [Build and retained-output verification](https://github.com/sunnyriverr/btx/actions/runs/42708038748).

Atlas is reused from its prior clean locked Rust1.95 build: its complete gui/atlas subtree, schemas, permissions, frontend and internal Cargo inputs are unchanged (treea0bab679). See [reuse audit](atlas-reuse.json). Package copies receive recorded RPATH edits; producer and packaged hashes are distinguished in [manifest](manifest.json).

Current bundler/runtime ownership logic is reused, preserving all78protected files including node, helper, guard, wrappers and OpenSSL. The compatible Qt runtime comes from the previous retained Qt6.2.4 candidate. This is deliberate retained-component assembly, not an untouched download. The full change and protection graph is in [assembly.json](assembly.json). Existing authors/licenses remain; JPP's adopted #452 and pending #477 are distinct. No #477 product changes or verifier ceiling override were included.

## Native acceptance

- Existing whole-archive gate passed without launch during assembly and with normal daemon launch before GUI. No guard-warning waiver. [Assembly log](logs/archive-gate.log), [normal gate](logs/normal-archive-gate.log).
- Packaged Qt rendered its actual regtest main interface; capture inspected. The window exceeds virtual-screen size, so this is not layout/UX qualification. [Qt capture](captures/qt-main.png).
- Atlas rendered, opened the real GTK cookie picker and native confirmation, independently matched the local endpoint/regtest/genesis, and showed LIVE LOCAL twice at least5s apart. [Connected capture](captures/connected.png), [GUI observations](gui.json).
- Separately, the identical archive passed two boots with Modelnet enabled and explicit offline policies:20node/helper health observations,20guard observations, persisted public identity and fresh child/guard boot identities.59assertions within one case, not59independent tests. No manual helper/guard launch. Clean RPC shutdown, no fallback signals, no remaining processes and runtime removed. [Lifecycle](lifecycle.json).

GUI connection used a wallet/Modelnet-disabled node. The enabled service restart is a separate profile; this does not show an open Atlas session reconnecting across that restart. No physical desktop, wallet/signing/spending, GPU/ExactReplay, mainnet sync, full suite, throughput, long soak or release signoff. The known genesis-sync defect is not changed.

## Prerequisites and reproduction

For this Ubuntu24 virtual-desktop recipe, ordinary desktop/runtime packages include GTK3/WebKitGTK4.1, **libayatana-appindicator3-1 and zenity**, GTK portal, libopengl0 and libxkbcommon-x11-0; node/runtime dependencies and the X11/accessibility observation tools are listed separately in [executed workflow](recipes/workflow.yml). The inherited release notes mention only GTK/WebKit and still need the tray/picker prerequisite correction. Observation tools are test tooling, not asserted end-user requirements. No newer Qt stack is installed for assembly; retained compatible Qt is selected explicitly.

The [acceptance run42720680125](https://github.com/sunnyriverr/btx/actions/runs/42720680125), fixture2f0146a447e926b1de0e0f40e0e71bed1c190c7a, is the executed entry point. Its original `.github/workflows/release-rpc-help.yml` pins source and input artifact run IDs. [Copied recipes](recipes/) retain the executed Python bytes; copying the workflow into a new branch is a reconstruction recipe, not a separately tested fresh producer path. Offline result controls: `python3 recipes/validate.py` from this evidence directory. They reject missing Qt/archive/picker/connection/capture/cleanup evidence, errors, skips and crashes.

[Download candidate artifact13719758757](https://github.com/sunnyriverr/btx/actions/runs/42720680125/artifacts/13719758757) (login may be required). Artifacts expire23November2026; full digests are in manifest.json. Small results/captures are retained here. Initial42720459427 failed before archive creation because a copied packager lacked its adjacent support manifest. The corrected fixture imports the original repository module; no component rebuild or successful GUI test was repeated. Original failure is retained in the manifest and CI.

Next decision: use this as the compatible Linux desktop build/package path, with explicit prerequisites, if accepted. The official0552 download remains unchanged. Pending review does not justify another test campaign.
