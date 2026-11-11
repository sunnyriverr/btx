# Native Linux follow-up evidence

## #477

A same-named library in an unrelated archive directory could make the gate skip a version requirement even though the ELF loader cannot reach that library. Check the requesting ELF’s search directories before treating the dependency as bundled.

With compiled arm64 ELF fixtures on Alpine Linux, both musl and Debian glibc 2.41 rejected the unreachable layout. The original gate accepted it and the patched gate rejected it. Both gates and loaders accepted the reachable layout. The runs used fixture ELFs.

## #454

An existing version floor that could not be opened was treated as absent. The poller now rejects an inaccessible floor or dangling symlink and still allows an update when the floor is genuinely missing.

On Alpine Linux arm64, the same poller test went from calling the recording installer to returning BAD_MANIFEST for both mode-000 and dangling-symlink floors. Missing, empty and readable higher-floor controls passed. The test used fixtures for downloads, signature verification and the installer.

The logs contain hashes of the original and repaired product files. See [patch identities](patch-identities.json). Jpp-matata authored the original changes.
