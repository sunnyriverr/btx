# Tested managed-helper profile restart

Verdict: current Linux node reproduces1GiB instead of saved8MiB after helper replacement; the focused patch makes the same maintained functional script pass completely.

Base release-0.34.17 at371013d61dc124a363521df5b94e97f64d2464f2. Product commit 0e259f14862b9066cea3ac786ef002280852d5aa. This evidence branch contains the exact tested five-file change plus this report; it is not the PR branch.

## Executed qualification

[Run43999682956](https://github.com/sunnyriverr/btx/actions/runs/43999682956), workflow032427814cfd5e9e6fe635865eb6e039342726ab. Ubuntu22.04 x86-64 container on an isolated Ubuntu24.04 hosted runner; GCC11.4, OpenSSL3.5.9 and Python3.12.16. Coherent production btxd, CLI, helper, btx-guardd and test_btx built normally from the pinned source, not a compatibility adapter.

- Same maintained feature_swarm_profile_overrides.py entrypoint: before exits1 at exact `not(1073741824 == 8388608)` helper-restart assertion; after exits0/Tests successful (65.2s).
- Candidate preserves8MiB/zero across helper replacement, stored settings and full-node persistence. Explicit16MiB storage and namedPERSONAL options remain authoritative. Existing follow/seed, mirror/idempotency, zero-spend, height0 and guardREADY→STOPPED checks remain enabled and pass.
- Complete modelnet_infra_tests selection:17baseline cases pass;18candidate cases pass, including the new maintained regression. Other unit suites were outside this filter.

Commands: `build/bin/test_btx --run_test=modelnet_infra_tests --log_level=test_suite` and `python3 test/functional/feature_swarm_profile_overrides.py --configfile=build/test/config.ini --tmpdir=<fresh-directory> --nocleanup`. Before running on baseline, overlay only the candidate functional script; restore it before applying the full product patch and rebuilding for after. The exact executed restoration/build/qualification recipe is [the fork workflow](https://github.com/sunnyriverr/btx/blob/032427814cfd5e9e6fe635865eb6e039342726ab/.github/workflows/profile-helper-restart.yml) and its proposal/build.py. Companion guard and configured Python shared-library path are required runtime prerequisites.

## Identities and limits

qualification.json records actual binary SHA256s, commands, exit codes, action counts and artifact identities. source-sha256.json records all five candidate source files. Native logs are unchanged. Infrastructure logs drop ANSI escapes and lines for disabled unrelated suites; complete raw logs remain in artifact14292016548, whose downloaded ZIP verified as d16cc7292f28ff9c8124c4736fe6b1a01aedf9226d39f88d8ed0406d29ffa138.

Compatible candidate build checkpoint14291528526 remains on the run until1Dec2026; remote ZIP metadata digest a39181bd0b29702d4bb7f64b3040816c181fbb1e1659a7629de873efb543521b. It was not downloaded/rehashed locally. This is a build checkpoint, not a release package.

Disposable unfunded regtest; no model acquisition/inference, real peers/funds, mainnet, Windows, current patchedMacdaemon, full unit suite or release qualification. Prior mixed Mac support-cache governor failures were not counted: coherent Linux suites pass without a governor product patch. Setup-only Git/loader, planning and missing-guard failures preceded the final successful run; they are not the expected before failure.

This extends the existing profile/supervisor implementation and maintained tests by Numair, JPP and contributors. Original copyright and author history are retained; no unmerged third-party repair was reused.
