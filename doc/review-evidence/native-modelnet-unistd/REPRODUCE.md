# Reproduce the bounded native include-route comparison

This is the exact component recipe executed in Windows run 41749124214. It does not configure the stock root, link the full Modelnet library or run test_btx. The same two production translation units are built in four separate source/build directories, using the accepted baseline and candidate WIN32 CMake blocks. The included payload pins the real source bytes and candidate adapter/test; its hashes are recorded in closure.json.

Prerequisites: an x64 Visual Studio developer command prompt/Windows SDK, clang-cl, CMake 3.22+ and Ninja on PATH, and Python 3. No vcpkg/OpenSSL or source edits are required for these selected objects. This does not resolve the full node's dependency requirements.

From the evidence directory, in that native developer command prompt:

```bat
where cl
where clang-cl
where cmake
where ninja
set "CL="
set "_CL_="
set "RUNNER_TEMP=%TEMP%\btx-unistd-review-%RANDOM%"
mkdir "%RUNNER_TEMP%"
python runner.py
```

Use a fresh RUNNER_TEMP directory. The script refuses to reuse an existing native-modelnet-unistd directory. Exit zero requires the expected baseline compile failures, candidate production-object builds, exact native header dependency trace, both production-object identities, and the same 10 runtime controls per compiler. Any setup, unexpected compile or runtime failure is recorded and produces a nonzero result.

Results, complete commands, source identities, compiler logs, compile_commands, dependency traces and retained test executables are under `%RUNNER_TEMP%\native-modelnet-unistd\evidence`. Read result.json rather than treating artifact upload as a pass. Object hashes are recorded; object files are not in the uploaded artifact. No network connection, model inference, node, wallet or process spawning is exercised by the control. Unsupported fork remains ENOSYS.

The standalone test source is `test/util/windows_modelnet_unistd_tests.cpp` in the product commit. It is not registered in test_btx. MinGW/Unix routing was checked by CMake condition evaluation only; native execution on those profiles is not claimed.
