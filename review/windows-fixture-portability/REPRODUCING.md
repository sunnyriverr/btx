# Executed entry points and reconstruction limits

The recorded fork run is [41997202444](https://github.com/sunnyriverr/btx/actions/runs/41997202444), controls commit `e4c2e7b5fdbe3831b123cfa7e03edb9d972bbae8`. Its immutable [workflow](https://github.com/sunnyriverr/btx/blob/e4c2e7b5fdbe3831b123cfa7e03edb9d972bbae8/.github/workflows/windows-root-configure.yml) is the executed entry point. The workflow and selected controls are copied under controls/latest; shared runner/checkpoint files and source bundle remain at that exact control revision. None of these packaging instructions has been executed as a fresh acceptance campaign.

The actual run restored exact cache 10045771520 and checkpoint aad9f31c on source 8a642b1e, verified the full source/profile/catalog, refreshed the Git index and checked out 473a2a0b. It used the original generated commands and appended a separately named component target to a hash-identical full Ninja graph. Plan/build both used an explicit -f manifest, rejecting root-CMake/glob/bootstrap and broad command invalidation. It then executed the maintained cases serially and captured a new source/profile checkpoint. The exact commands are in latest/run-record.json; the latest scoped build used Ninja -j4 -k1.

The invoked stages, in the workflow's native tool environment, were:

    python controls/contrib/devtools/windows-root-configure/fixture.py prepare
    python controls/contrib/devtools/windows-root-configure/fixture.py build
    python controls/contrib/devtools/windows-root-configure/fixture.py run
    python controls/contrib/devtools/windows-root-configure/fixture.py retain

These stages require the recorded original source bundle, shared runner/checkpoint modules, Windows paths/toolchain, static OpenSSL/vcpkg closure and exact cached graph. The copies here do not claim to be a standalone cross-platform runner. Older campaign controls also retain their original source identities; do not substitute the review commit ID and claim the old binaries executed it. Git-tree equality maps the packaged code to the executed final source only.

A missing/expired cache or artifact is an external prerequisite; do not silently substitute an unrelated mutable build or invent a pass. A fresh standard project build is a reconstruction/acceptance step still to be performed, not a result delivered here. The full maintained target currently retains known portability blockers and is not expected to be green solely from this series.

The new exact-profile candidate cache 10047590725 / checkpoint 4c2cf014 retains 3830 objects with normal Ninja dependencies. Original cache 10045771520 remains intact. See latest/cache-receipt.json; do not manually edit Ninja log/dependency metadata or relabel the cached btxd, which was not relinked during these component tests.
