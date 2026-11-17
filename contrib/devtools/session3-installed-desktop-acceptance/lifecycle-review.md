# Installed lifecycle draft — source review only

Prepared for Session 3's Linux desktop acceptance. This is a draft, not an executed result. No interpreter import, syntax compilation, native test, BTX launch, archive restoration, build or post was performed for this preparation.

## Scope and reuse

The supplied installed prefix is the only executable source. The parent must first hash-admit candidate artifact 14319148652 / inner archive 915fae283089a325df65ef7521fffd6e30f5faa8d0bc8f2d77a2b6af52348a57, install it using the accepted prebuilt-tree routine, and preserve the explicit packaging-overlay identity. This script does not download, extract, install or rebuild anything.

Session 2's retained runtime/case.py and successful historical run 43499330842 supply the ordinary two-boot recipe. Their source88 result is not carried forward as a pass for the current source074 candidate. The new draft takes --prefix, --runtime and --out. Runtime itself must be fresh; prefix/runtime/output may not contain one another in a way cleanup would remove evidence or installation. The parent owns the enclosing unique temporary directory. Both boots reuse the same private datadir, not a real wallet. All node startup is regtest, wallet-disabled and network-disabled. Model bind, host, demand seed, peer following and LAN discovery are disabled; a16MiB payload quota is explicit.

## Source mapping checked

Read-only GitHub file inspection at 074dac167c26c1e091198f691ed5727817dba88a:

| File | Git blob | Reviewed contract |
| --- | --- | --- |
| src/init.cpp | 55e11d82667c1398591e486b903efba966284b93 | model bind/host/storage/seed/follow/LAN arguments exist |
| src/rpc/modelnet.cpp | d3657694ed9602fe03052647106a3639b2294646 | node proxies getmodelnetworkinfo and augments helper ownership/state/ready/restart/PID; listmodelidentities proxy; typed modelsecurity status dispatch |
| src/modelnet/supervisor.cpp | ffb2d96a2b3f84c3d06e937edbbbc0ea59db8298 | helper argument propagation for quota/seed/follow/LAN; no modelbind argument for an empty disabled bind |
| src/modelnet/helper.cpp | b38493dcd0cc8d3d2ee9653c1c04de8433752419 | quota_bytes, seed_mode, follow_configured_peers, automatic_spend_atoms and public/advertised flags; local identity catalog |
| src/modelnet/guard_supervisor.cpp | bad2adeaa620cda550167adebd26c79cf0fd5c66 | shipped regular sibling btx-guardd lookup |
| src/modelnet/security_v2/service.cpp | a82f01fdba9c2854e6860db2876678fc2fcc102e | ordinary status returns guard_boot, string automatic_spend_atoms, policy_installed and journal_valid |

These are source applicability checks, not compilation or runtime proof. The guard call is ordinary startup/status only. No adverse-input, key, policy installation, retrieval, cancellation, inference, funding or swap behavior is included.

## Acceptance and containment review

Each boot checks the actual installed daemon and direct-child helper executable paths through /proc, stable PID/start-ticks identity, zero helper fallback restarts, wallet-disabled offline chain at height0, no peers and no advertised host. Ten observations per boot require both helper health and an answering node-owned installed guard. The second boot requires fresh node/helper process identities and guard boot, and unchanged local public identities. Package file hashes must remain unchanged.

Normal CLI stop and exit0 are required after each boot; remaining installed processes fail the phase. Cleanup first tries normal CLI stop after an intermediate assertion failure, then may signal only current executable/start-ticks-matched records under the unique installed prefix. Any fallback signal, surviving process or unremoved owned runtime forces FAIL. Raw cookie/key files and private runtime are not published; output includes only the scoped observations and console/debug logs.

SIGTERM/SIGINT enter failure cleanup. Parent timeout handling must allow at least60seconds for the cleanup path before forcibly ending the controller, then independently inspect the unique installed prefix for survivors. The parent collector must require this phase's exit0 and result.json overall PASS; absent/timeout/error results fail closed. The controller must not run this phase concurrently with the GUI phase against the same prefix.

## Remaining evidence

Draft has not been syntax-checked, imported, compiled or executed. The exact candidate still needs full outer/inner hash verification on the future runner and actual installed startup/restart qualification. No current GUI, lifecycle, release or official-asset PASS is claimed.
