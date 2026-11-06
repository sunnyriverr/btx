# RPC-help independent checks — native evidence

**Qualified fd162036:** all five checks run on a real accepted666 node; conversion and argument-name failures still produce exit1. Categories, help generation and wallet help across restart pass. Full RPC-help is not green.

Code: fd162036b6b8b6212d4f7f3ec4a234acce3a7392, one three-file commit on666673a3153225ba264c7870e0e82e354df86765. The change retains strict table/name assertions, supports current conversion-row flags, collects check failures, and derives exact category expectations from compiled Modelnet/wallet features.

## Executed native qualification

[Run42188105197](https://github.com/sunnyriverr/btx/actions/runs/42188105197), fixturefe62ec042c89bb6cde2d8c0cfd1f64c3d6314ad2. Ubuntu24.04 x86_64. Reused previously built accepted666 node/CLI from immutable cache10096149671; no compilation/relink/cache save. Build profile walletON, ModelnetON; runtime Modelnet disabled. Both variants use a fresh0-height peerless regtest with ordinary framework corepolicy/softwareexpiry/seal test settings. No mining/model workload.

| Check | Parser-only7f48 reference | fd162036 |
|---|---|---|
|Client/server conversion comparison|Fails208triples|Fails identical208triples|
|Argument-name consistency|Unreached|Fails on actual mixed declarations|
|Categories|Unreached|Pass|
|Help dump|Unreached|Pass|
|Wallet help and -nowallet restart|Unreached|Pass|
|Process exit|1|1|

These are208mismatch triples, not208independent bugs. No allowlist or mismatch removal. The native wrapper only observes stage results and applies the same disposable fixture to each variant. It does not inject these failures. Both final failing stage names remain in the final assertion/log.

Node SHA2564ad63b64f6d6bab34f5ba92518dc8955ee2e263e0daa4d739f27ec868fce0ae1; CLIb71061e57a9224d86ef2f17da1914f3b68ffe91b696282151c0aba9e12caa5b8. All14,309tracked source bytes/modes and binaries unchanged before/after. Four pinned OpenSSL files and CMakeCache hash match native-expected.json. Native artifact13488915671 SHA256c8c0d82c96f59f2264e861b68b7a501962e7c3d58257ad804fd2e6b1d2faf047 was verified; readable records are preserved here independently of artifact expiry.

## Reproduction and local controls

The exact executed invocation is native-workflow.yml; native-run.py and native-case.py contain the executed driver. It checks out accepted666 separately, restores the original branch-scoped cache, verifies inputs, then invokes case.py for each variant through the normal functional framework. Full arguments/exit codes are in native-records/result.json. native-dispatch.json identifies the original contrib/devtools/rpc-help-live paths. These scripts are preserved evidence; the renamed files here must be restored to those paths to reconstruct that CI recipe. There is no promise that an expired/private cache can be fetched by another reviewer.

The existing generated config gets explicit ENABLE_MODELNET=true from its verified CMakeCache setting. Root configuration/build was not repeated. Actual per-variant create_test_config/template generation was separately executed locally for ON/OFF/Y/NO. verify.py uses actual Python test methods with local doubles/fault injection: eight orchestration scenarios plus14method controls pass. Eight parser controls pass on the final unchanged parser; parser.log records that run. configure-check.py's path setup and exported CMake/template inputs are documented in its script; candidate.patch gives all three final source changes.

## Limits and setup corrections

No native Windows/macOS node execution, ModelnetOFF native build, helper serving, full suite, GPU, live-network or release qualification. Configuration normalization is local proof; runtime metadata/help is real Linux-node proof. Wallet help's restart records normal Shutdown: done. Both final intentionally failing tests use the existing framework failure path: TestNode's destructor kills remaining nodes. No runner fallback signals or surviving owned processes; disposable data removed. Final shutdown is not claimed graceful.

First attempt42187687695 stopped before checks because fixturelisten0 conflicted with the framework's loopback bind; corrected to connect0. Second42187873591 exposed missing Bridge/Shielded expectations; exact wallet registration confirmed them and final category checks include them. These attempts are retained as setup/correction evidence, not final passing qualifications.

Authors of the existing Knots test retain their source headers. Sunny River prepared this correction and its Codex-assisted test tooling. No product RPC or validation behavior changes.
