# RC independent-oracle Windows qualification

**Tested fixture repair `6d269ab5`: the original registration failure passes after repair under normal optimized linking; duplicate-provider rejection remains enforced.** Reported by [JPP/Jpp-matata](https://github.com/btxchain/btx/pull/432#issuecomment-6750408409).

Code: `6d269ab5372268d89f9f1ed213c0a63337ce71b1`, based on release `dac9aee53520bd49ed320ec7a49b9072fc7d88d9`. Exact tested tree: `dd2e49e4f6e62755372f6e3c70890c22c75b4af4`.

The alternate test oracle was an identical forwarding wrapper. Optimized linking folded it to the primary callback's address, correctly triggering the test-only independence guard. The patch uses a separate scalar implementation and adds arithmetic/output-replacement coverage. Both existing regression and duplicate-rejection test bodies are unchanged. Provider admission and validation rules are unchanged.

| Maintained case in `matmul_v4_rc_tests` | Stock before | Candidate after |
|---|---|---|
| `rc_strict_independent_same_digest_rejects_false_header` | abort: second registration (4 assertions passed, 1 failed) | PASS,15 assertions |
| `rc_strict_same_callback_cannot_masquerade_as_independent` | PASS,15 assertions | PASS,15 assertions |
| `rc_independent_oracle_matches_reference` | new | PASS,6 assertions |

Original before evidence: [run42735908793](https://github.com/sunnyriverr/btx/actions/runs/42735908793), stock binary SHA256 `446a2d951095f9274a083af475a504c6f7ebd5c50782e2cb69a6150459ab4b00`. That valid immutable result was reused, not rerun. See [before XML](before.xml) and [failure](before-failure.txt).

Candidate: [successful native run42746956548](https://github.com/sunnyriverr/btx/actions/runs/42746956548), binary SHA256 `8ba64adb99f9aeee77a1eff5e0b3260fee6126a335117b8936e865ef6ac7ce59`. Windows Server 2025x64, clang-cl 20.1.8/lld-link, MSVC 14.51.36231 libraries, SDK 10.0.26100, Release/O2/static CRT; Modelnet/wallet/tests/ZMQ ON, GUI OFF. One test object recompiled in 14.312s and one relink in 8.281s using the saved exact project inputs. Three cases / 36 assertions pass in 1.719s, with no timeout. No ICF/NOICF override was used; [normal map excerpt](normal-callback-map.txt) shows distinct callbacks. The earlier NOICF experiment diagnosed cause only, not repair qualification.

## Reviewer entry point

Use the maintained cases above in a configured Release `test_btx`. The actual executed entry point is [this immutable CI controller](https://github.com/sunnyriverr/btx/blob/e2a4ea18b3e6d2d65089a58107fc6dafe479caef/contrib/devtools/windows-root-configure/consolidated.py), stage `run`. It verifies the saved stock cache, applies the exact one-file patch, compiles that target and relinks normally, then invokes each named case separately with `--run_test=<suite/case> --log_level=test_suite --report_level=detailed --report_format=XML --report_sink=<owned-path> --catch_system_errors=yes -- -testdatadir=<fresh-owned-path>`. Exact invocations are in [executed-commands.json](executed-commands.json); [compile-command.json](compile-command.json) and [link-argv.json](link-argv.json) retain the native build flags. This retained-cache controller is not a clean-build recipe. The normal repository build/test instructions apply for a fresh checkout.

Raw case XML: [arithmetic](after-1.xml), [original regression](after-2.xml), [duplicate rejection](after-3.xml). [results.json](results.json) and [manifest.json](manifest.json) bind identities/hashes. Cached build-info retains the baseline string; the tested tree/file/object/binary identities establish the candidate.

## Limits

**The full Windows unit run is still incomplete (#356).** This is one fixture translation-unit rebuild and targeted native qualification, not a full rebuild, full-suite pass or release sign-off. No Linux/macOS execution of this patch, physical accelerator or live-network behavior is claimed. Original source and all 5,901 objects / 12,858 cached files were restored and hash-verified; no cache save or surviving owned process/runtime remained. The candidate result is kept separate from stock-source acceptance counts.
