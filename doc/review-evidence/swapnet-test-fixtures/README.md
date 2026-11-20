# SwapNet startup test evidence

Both test-only patches target release-0.34.17 at 4134c67f. All four focused tests passed in a clean copy with the two test patches on macOS 26.5.1 ARM64 and CPython 3.12.10. This check used the Python host and disposable stores. It did not run a native node, Linux or Windows.

## Embedded startup tests

The fixture drives the real Python startup and Bitcoin wallet selection with simulated RPC replies. It checks that a refused explicit Bitcoin endpoint does not trigger automatic discovery, a discovery timeout clears after restart, and a corrupt wrapping key causes startup to fail without replacement. Each corresponding assertion failed under a deliberate scratch-only change that broke its safeguard.

## SQLite fixture

On the same Mac interpreter the original fixture failed before installing its hook because it used a Linux library name. The new fixture resolves SQLite through Python's loadable extension. The original quiet-startup assertion passed and an injected SQL error made it fail. An additional Mac CPython 3.11.14 build with built-in SQLite skipped explicitly.

[Focused result](focused.txt) · [SQLite controls](sqlite-controls.txt) · [Review receipt](receipt.json)
