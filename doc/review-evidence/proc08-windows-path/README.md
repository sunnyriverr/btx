# Proc08 Windows separator qualification

**Same two tests FAIL before / PASS after; full Windows unit run remains incomplete.** Code: [358d8fd5](https://github.com/sunnyriverr/btx/commit/358d8fd529f657a1190ec4f3d09634684c6b96c5). Refs #356.

Normalize `\` to `/` under WIN32 before the existing comparison. Native inside paths had been accepted; the existing file-boundary condition, POSIX literal backslashes and qualification flags remain. This fixes a demonstrated component/unit failure; the caller audit found only the tracked unit caller. No live-node impact is claimed.

| Exact selector | Without product fix | With product fix |
|---|---|---|
| proc08_tests/evidence_and_research_path | 74 assertions pass /3 fail | 77 pass |
| proc08_tests/research_path_separators | 35 pass /17 fail | 52 pass |

## Provenance and scope

Native [run42455319004](https://github.com/sunnyriverr/btx/actions/runs/42455319004): Windows Server2025 x64, clang-cl20.1.8, MSVC14.51.36231 libraries, SDK10.0.26100, C++20/staticCRT/OpenSSL3.5.4; Modelnet/wallet/tests/ZMQ ON, GUI OFF. Test-only control `92b0c884f21e36a350194b746d1bd7f083d4aff4`, candidate `7a9681dd0dc68965520da809cf0230772e6dc7de` on source37472d88. Identical test-file SHA256 `b0b6450baac645b10fb9c1fc9c7d348a0b5c040a4c796a713d2efdd79024c87d`. Product-only difference between those trees: three lines. The original77assertion test body is unchanged.

The publication commit is two files on swarm `d522af520f55067bd470fdcc0c246e3b4d3a26fc`. Both source/test blobs exactly match the native candidate; both baseline blobs are identical on tested37472 and swarmd522. The tested integration includes previously disclosed #436 paths/credentials, #437 fixtures and adopted #433. **Neither historical binary is a fresh build of the publication commit or stock release.** See [code mapping](code-receipt.json), [verification](verification.json), [raw paired logs/XML](records/).

The new regression includes physical-file equivalence, native/mixed/forward inside paths, trailing separators, outside acceptance followed by inside refusal, prefix siblings, ABSENT/FIELD and all qualification flags. Original137passing cases were not rerun. Build18.42/10.39seconds; only5objects changed across both stages,5880preserved; dependencies/compile commands unchanged, no cache overwrite. Test processes, data and short-drive mapping cleaned up.

macOS arm64: the actual component and seven real headers were compiled with C++20/-Wall/-Wextra/-Werror;17observations each before/after are identical, including literal-backslash outside/inside filenames, outside/prefix and refusal controls. This is component execution, **not full POSIX units or native Linux verification**. [POSIX record](posix-verification.json) has workspace paths replaced for publication; original record hash remains in MANIFEST. Driver and actually executed cache controller are retained under recipes/.

## Running the maintained tests

In a configured native Windows BTX test build, run separately:

```
test_btx.exe --run_test=proc08_tests/evidence_and_research_path
test_btx.exe --run_test=proc08_tests/research_path_separators
```

The native campaign used those exact selectors plus the recorded XML/report and temporary-root flags. On the test-only control both fail; on the candidate both pass. Recipes retain the executed cached-build harness; a fresh-machine setup or whole-suite run is not claimed. Raw CI archive SHA256 `5be46e66950acffb9819cc5213dc5d06038bc6f9df176e4f635cb10b0aa137dc` is retained as provenance; ordinary branch files are the primary review surface.

This is a separator repair, not complete containment/canonicalization: case folding, dot segments and symlinks are unchanged. No desktop, full Windows/POSIX units, live-network or release qualification. Original license/copyright retained; credit repch1c and Jpp-matata for Windows prerequisite findings/review context. The hosted runs above are ours, not attributed to them.
