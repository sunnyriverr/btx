# Windows snapshot I/O evidence

Code: 23d860d17405a24a9bb0921b2be9cb8e44787816, base cbf65894e6d61084527cd93e913a00c6794418dd. Native Windows failure reported by repch1c in btxchain/btx#356 item4.

Run `python3 run_tests.py` from this directory on a POSIX host with clang++, C++20 and Homebrew OpenSSL3 at the paths in the script. This is a retained Mac component recipe, not a portable Windows test suite. Requires1.25GiB free space. The sparse fixture has4.295GB logical size but266240 allocated bytes on the tested APFS filesystem; it is deleted after execution.

The recipe executes the exact extracted production reader/helpers, with small offer/filesystem and OpenSSL SHA256d adapters. Original and corrected POSIX versions both pass normal128KiB reads and offsets at2GiB and above4GiB, partial-tail and error controls. A deliberate int32-narrowed seek passes normal reads but fails the large offset test. Candidate probes size/rewind directly. This is not a complete linked node or a full multi-GiB offer hash/manifest test.

Both complete production source variants pass native Mac syntax/type checking with retained pr340-multiwindow generated configuration and headers. Those commands/logs are provenance; paths marked[workspace] refer to that retained local cache, not a standalone clean build recipe. No object/link/native Windows result is claimed.

Native Windows compilation with actual CRT headers and execution of ordinary/large-offset tests and existing snapshot tests remain required. No before-failure on Mac is claimed; it already uses64-bit POSIX offsets. Windows adapter choice was independently source-reviewed; that is not Windows execution.

The JSON/log paths are sanitized; source and executed harness bytes are unchanged. Detailed local publication/resource records are deliberately outside this evidence directory.
