# MSVC 19.44 MatMul compile check on c97c9a8d

All three MatMul sources that failed in [bs1812's a97af7b3 Windows report](https://github.com/btxchain/btx/pull/714#issuecomment-6989117716) compiled on `c97c9a8d00ea37359b8691fd25c783725c1f4021`, which includes [Numair's 88eaf942 repair](https://github.com/btxchain/btx/pull/714#issuecomment-7002652392).

| Source | Exit | Compile time |
| --- | ---: | ---: |
| `matmul_v4_rc_freivalds_i8mm.cpp` | 0 | 3.12 s |
| `matmul_v4_rc_freivalds_sampled.cpp` | 0 | 5.80 s |
| `matmul_v4_rc_fri_ext3_alg.cpp` | 0 | 8.78 s |

Windows Server 2022 x64, MSVC 19.44.35230, VS 2022 toolset 14.44.35207, SDK 10.0.26100.0, Release, `-openmp`. The fresh runner restored the dynamic `x64-windows` vcpkg prefix and verified all 6,669 files. Wallet, tests and ZMQ were enabled at configure time, with ModelNet and GUI disabled.

CMake used Ninja to generate the commands. The job generated the shared build-info header, ran the [three commands](three-commands.json) directly and verified three AMD64 COFF objects. The baseline used the Visual Studio generator. No full build, linking, unit tests or baseline rerun.

[CI run](https://github.com/sunnyriverr/btx/actions/runs/44495658922) · [Executed workflow](https://github.com/sunnyriverr/btx/blob/e9de6bb089d67627673fb890bf30f5886b843aa9/.github/workflows/msvc1944-c97-configure.yml) · [Result and checksums](result.json)
