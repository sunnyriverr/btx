# ModelNet cursor and offline bundle short-write results

The matched fixtures ran on macOS arm64 with Apple Clang. The release baseline is `c6f9678dd225572528d06c456c16eb4c78bc637c`. The candidate is `7ceca1d08849d5e943d69fb13ac7a62fb907f7df`, tree `198c97c233fa36be1663c8672fa424c08f799538`, based on #576 at `1ccb08cf036ad029565e11c1884a231f0f0b444e`.

Both fixtures cap the process file size at eight bytes for one replacement. Both baselines failed the preservation assertion. The candidate hydration fixture reopened the old cursor and read from 4 MiB through a local origin callback. The candidate bundle fixture re-imported the old bytes and compared the retry with a healthy export byte for byte. See [results.txt](results.txt) and the [recorded hashes](verification-sha256.txt).

These are component builds of the real ModelNet writer, reader and hydration code with fresh state objects. The build script records the macOS component commands and their staged release-source inputs. Full helper restart, live S3, lab RPC, and native Linux and Windows project builds are outside this run.
