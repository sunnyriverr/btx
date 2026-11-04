# Native Windows supervisor PID header — verified compile repair

Code: `68a17f15ac21ef2295c0e492ede35063f0afd921`, base `46caec762b0f130d497313d8ca9fa6894ac19ccd`. Only `src/modelnet/supervisor.h` changes.

The real daemon `init.cpp` includes this public header outside Modelnet's PRIVATE compatibility includes. Native Windows has no declared `pid_t` there. Windows now uses an inactive signed-int sentinel on its already unsupported spawn path; POSIX retains `pid_t` and explicitly includes sys/types.h. Every real child-ID write/spawn/wait/kill stays in unchanged POSIX code. Thanks to repch1c for the Windows inventory and JPP for native investigation.

| Actual check | Original | Candidate |
| --- | --- | --- |
| Root-generated bitcoin_node init.cpp object, native clang-cl | Unknown pid_t at supervisor.h:103 | Produces object |
| Actual header first, native MSVC cl | C3646 at m_pid | Compiles |
| Actual header first, native clang-cl | Unknown pid_t | Compiles |
| Mac actual header closure/type/layout | Pass | Same pid_t, size520/align8, identical class tokens |

Native Windows Server2025 x64, clang-cl20.1.8, cl19.51.36260/toolset14.51.36231, SDK10.0.26100.0, C++20/static CRT. Project preset windows-clangcl-static: tests ON, default Modelnet/wallet/SQLite/ZMQ ON, GUI OFF. [Actual paired job](https://github.com/sunnyriverr/btx/actions/runs/41771698640), exact CI controls b8057204ff0bf3d7dd7e594ce670957532654f01. The source catalogs cover14307 tracked entries; only the approved header differs. All19 command logs, three objects and the unchanged actual compiler command/database are verified locally. Full catalogs/database/objects are in that job's artifact; its download digest is recorded in native/artifacts.json.

## Reproduce on native Windows

Use an isolated checkout of the exact base and the project's native clang-cl toolchain/dependencies. Configure using the recorded preset/options in native/runner.py and native/CMakeCache.txt (OpenSSL3.5.4 static and pinned vcpkg). The recorded hosted job reused verified dependency caches; it is not a clean dependency rebuild.

After configuration, run the same generated target on each header variant:

```powershell
cmake --build D:\btx-native-035\project-build --target src/CMakeFiles/bitcoin_node.dir/init.cpp.obj --verbose -- -j 1
```

The original must fail specifically at supervisor.h103 unknown pid_t. Replace only that header with source/candidate.h (hash in source-manifest.json), rerun the identical command, and require a new object. Do not add forced includes, disable Modelnet or modify compile flags. native/runner.py is the actual executed controller; native/workflow.yml records checkout/cache/compiler initialization. Its configure stage performs this exact pair and the two direct compiler controls. Direct-header probe and generated compiler command are retained alongside the logs.

Mac evidence used the real nine-header dependency closure from the same base, not header stubs; posix/ contains the fixture and the executed probe/script/logs. posix-check.py's default repository path is the original local source location; change R to your immutable base repository location to inspect the unchanged implementation hash when rerunning elsewhere. No real child process lifecycle was executed.

## Limits

This clears one real daemon consumer compilation blocker. It does not establish full daemon build/link, test_btx build/run, native Linux/MinGW, supervisor process lifecycle, Windows helper spawning, GPU, wallet/network operation or release qualification. The accepted supervisor.cpp is byte-identical. Two local missing-header fixture-assembly pilots were corrected before the final Mac pair; the Windows pair used one final reviewed run.

Original verification/product records retain their test-time unpublished status. Publication receipt is maintained separately; this does not change the tested bytes.
