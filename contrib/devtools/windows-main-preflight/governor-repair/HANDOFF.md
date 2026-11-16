Bug: an existing unreadable or malformed governor permit enables optional helper work. The focused repair is qualified; upstream publication remains held.

- Change only the governor reader: preserve genuine absent-permit standalone behavior; refuse existing open/read/parse errors. Both seed permission and automatic preservation use it. Generic store JSON semantics and upload pacing remain unchanged.
- Native Windows: same four maintained consumer cases, baseline healthy PASS / three defect cases FAIL; candidate 4/4 PASS, 159 assertions, zero selected skips. Separate corrected raw-file integrity and missing-parent recovery controls: 2/2 PASS, 13 assertions. They do not replace the strict consumer denial tests.
- Native Linux: same real two-helper workflow before/after. Baseline acquired models with malformed and EISDIR permits. Candidate refused both, recovered both original models after enabling, acquired a fresh third model, verified exact bytes, and stopped/cleaned both helpers.
- Limits: Windows evidence exercises linked seed-permission consumers, not native Windows helper transport. Linux is strict-PQ1 loopback, tiny public model data, not production or throughput qualification. This does not guarantee publication of a newer pause if its writer update fails, or qualify the full Windows unit suite.

Evidence and reproduction
========================
Accepted source: 1e2f8b5f12295002334d3390c12cac0bb4ae2aff. Windows additionally retains exact #746 fixture prerequisite; it is still open, not adopted. No source rollover.
Tested POSIX controller: e92ff5d6f7590b4420f908e083f8f4200b7521e4.
POSIX run: https://github.com/sunnyriverr/btx/actions/runs/43803093137
Windows baseline: https://github.com/sunnyriverr/btx/actions/runs/43795304277
Windows candidate: https://github.com/sunnyriverr/btx/actions/runs/43797580979
Windows supplementary controls: https://github.com/sunnyriverr/btx/actions/runs/43799780544

focused-candidate.patch contains only helper.cpp, resource_governor_tests.cpp, a corrected writer comment and the maintained native POSIX fixture. Apply against the accepted source; retain #746 only when reproducing its Windows test-build profile. The POSIX runner uses the normal btx-modeld target. Invoke the identical maintained script with --helper /absolute/path/to/btx-modeld --output /absolute/path/to/result.json for each binary. It has no baseline-mode switch: the unchanged phases produce exit 1 and the two named product defects on baseline, then exit 0 and all controls passing on the candidate. The controller checks those exact outcomes. POSIX setup/controller and retained checkpoint inputs remain under posix/ at the tested controller commit.

Native Windows profile: Windows Server 2025 x64, clang-cl20.1.8, MSVC14.51.36231, SDK10.0.26100.0, Release/static, wallet/ModelNet/tests/ZMQ ON, GUI OFF.
Native Linux profile: Ubuntu22.04 pinned container on hosted Ubuntu24.04, GCC11.4.0, OpenSSL3.5.9, CMake3.31.6; restored verified private build, normal target/complete generated graph. Candidate changes helper.cpp only.

The baseline raw-file fixture assumed every open succeeds during Windows replacement. Its correction permits only ERROR_SHARING_VIOLATION for unsuccessful Windows opens, requires writer/read progress, and preserves full JSON integrity for every successful open and POSIX open availability. Candidate-only supplementary results are not represented as matched fail-before evidence.

Credit and review
=================
Existing product/fixture authorship remains in the accepted history. The new repair and regressions are Sunny's contribution; no external platform ACK is claimed. A bounded internal read-only review checked the precise repair, fixture and claims. Its two prior findings (completion accounting race and budget cleanup) were corrected in the tested e92 controller; final review found no remaining concrete blocker.

Remaining campaign work
=======================
This focused repair is not waiting on the unrelated 15,511-case accounting. That account remains unfinished: preserve the 85 baseline passes, separately classify historical evidence/applicability and run only required uncovered groups. The full Windows unit gate remains open.
A clean focused product branch/commit and local wiki/cursor synchronization remain to prepare after disk recovery. This evidence branch is not an upstream PR. No new execution was requested by adding this report.
