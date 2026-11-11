# ModelNet watch removal verification

On release base `c6f9678d`, blocking the temporary watch file caused direct removal and disabling a mirror watch to report success. A clean helper restart restored the watch. The patched helper returned `IO_ERROR`, retained the watch live and on disk, and removed it across restart after a healthy retry. The unrelated watch survived. Mirror retries use a fresh idempotency key for the new attempt.

## Reproduce

Build `btx-modeld` from the base and the parent commit of this evidence branch. The measured builds used AppleClang on Apple silicon macOS, static OpenSSL 3.6.3, ModelNet enabled, tests/GUI/wallet/Metal/ZeroMQ disabled, and Release with `-O0 -g0`.

Run `python3 helper-regression.py /path/to/btx-modeld` against each build. Set `BTX_OPENSSL` if the matching CLI is outside the default Homebrew path. The harness creates its own temporary stores and uses Unix RPC only. Expect exit 1 on stock after both false-success cases and exit 0 on the candidate. [Stock](native-before.log) · [Candidate](native-after.log) · [Binary and source hashes](matched-receipt.json)

The maintained `unwatch_drops_the_actions_the_watch_queued` case in `src/test/modelnet_watch_tests.cpp` was run through an isolated Boost fixture linked against each helper's actual CMake archives. It failed on stock and passed all 21 assertions on the candidate, including preservation of the unrelated queued action. [Stock](queue-before.log) · [Candidate](queue-after.log)

The untouched stock Mac archive also reproduced both failures. [Archive receipt and results](package-before.log)

Full `test_btx`, daemon RPC forwarding, other platforms and a rebuilt release archive were outside the test scope. The logs replace transient local paths with placeholders.
