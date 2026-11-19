# Clang 18.1.8 / libomp object verification

The three generated commands compiled successfully at `a97af7b3f379e33e3ec65db948468d875ade2841` on Ubuntu 22.04 x86-64. Each used Clang 18.1.8 and `-fopenmp=libomp` and emitted an x86-64 ELF relocatable object.

| Translation unit | Exit |
| --- | ---: |
| `src/wallet/shielded_wallet.cpp` | 0 |
| `src/matmul/matmul_v4_rc_stage3_v13_terminal_fold_parent.cpp` | 0 |
| `src/test/matmul_v4_rc_stage3_multirow_v11_unified_verifier_air_tests.cpp` | 0 |

The runner used SQLite wallet and test targets enabled, ModelNet and GUI disabled. It verified 13 generated inputs and ran the three retained compiler commands directly, skipping the broader Ninja dependency build. No link, unit tests, full build, or separate baseline rerun.

Thanks to Jarek for the Clang failure report and Numair for the three fixes. [Original report](https://github.com/btxchain/btx/pull/714#issuecomment-6964571992) · [Numair's follow-up](https://github.com/btxchain/btx/pull/714#issuecomment-6965357185).

[Recorded commands](compiler-commands.json) · [Checksums and compiler receipt](receipt.json) · [Fork run](https://github.com/sunnyriverr/btx/actions/runs/44475409785) · [Executed workflow](https://github.com/sunnyriverr/btx/blob/6ae66b0615a8fb1f88d687c231d7c6cd4a2c313c/.github/workflows/clang18-openmp-configure.yml).
