# Backend linkage evidence

Credit to repch1c for issue356item7. Code commit d1ee21e828df480d6a3b9605a0d08a21fce8c6ef removes duplicate fallback ownership. REPORT.md states exactly what passed and what remains unverified.

On macOS with Python3 and Apple Command Line Tools, from this evidence directory:

    python3 prepare_inputs.py /path/to/btx-checkout
    python3 run_checks.py

The checkout must contain the code commit and its base. Input export refuses mismatched existing files. This uses actual repository headers/stub bodies but Mac-native ABI/linker, plus explicitly marked strong-linkage and enabled-provider controls. It is not a Windows/GPU/full-node build. Keep at least1.25GiB free plus10MB test headroom.

command-logs.txt bundles the recorded logs by command label. results.json records the original commands and statuses; personal workspace prefixes are replaced with [workspace]. Reproduction generates individual logs under build/. identities.json retains hashes of original inputs and local build artifacts, not a promise of identical binaries on another toolchain. Code branch: codex/fix-backend-stub-ownership. The PR links this evidence at an immutable commit.
