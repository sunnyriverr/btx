# Corrected Ubuntu attempt — fixture blocked before installation

18 November2026 Brisbane. [Run44193516952](https://github.com/sunnyriverr/btx/actions/runs/44193516952), control147599195585825a066cb722a2dc6a05aa5155eb, one authorized corrected attempt on the isolated Session3 branch. Ubuntu24.04 x86_64 job104seconds. **Workflow failed; installed desktop acceptance remains unproved.** Same retained archive; no rebuild or upstream post.

## Actual evidence

| Boundary | Result |
| --- | --- |
| Exact change/ref/payload | Four changed remote Git blobs/modes verified: dependency workflow at its two locations plus its two manifests. Installer/runtime/GUI/lifecycle inputs and archive/source pins unchanged. |
| Complete outer ZIP | Metadata and complete download/SHA256d9f58d9623a3e6d13b15b9e67ba2c2b16bb9b574985bbc9dcd69c4aed3daa664 passed again, artifact14319148652/run44063898937. |
| Host dependency correction | Passed in80seconds. Complete dependency download selected mirrors.edge.kernel.org, then offline APT install succeeded. This does not prove fallback to another mirror; the same first mirror was reachable in this attempt. |
| Display portal | Actual FileChooser probe returned uint32 version3. Openbox started. Warnings about RealtimeKit/PipeWire did not stop this probe; GUI behavior was never reached. |
| Archive admission | Failed in our fixture's directory-mode restoration at accept.py:155. Trace shows a nonexistent extracted/btx-0.34.16/btx-0.34.16 path. The controller reached this line after its inner archive/provenance-record digest checks, tar type/size/mode/link checks and extraction. The final extracted-files inventory comparison was not reached; do not label complete admission PASS. |
| Installer, Qt, Atlas, lifecycle | **Not run.** No installer.log, GUI/lifecycle result or screenshot exists. No BTX binary or daemon was launched in this hosted attempt. |
| Cleanup/completeness | Actual result overallFAIL, phases{}, cleanup_signals[], cleanup_remaining[], runtime_removed=true. payload_unchanged=false reflects the missing installed-prefix baseline, not an observed changed payload. The completeness collector correctly failed. |
| Retained evidence | Artifact14377782947,28,661B, SHA2560b9cc9768fa4f469e03a18c22744f70e7b50e5fa32abfb86a760211d63adfbc9, downloaded/hash- and CRC-verified locally. Seven files: metadata, prerequisite/host/portal/window-manager records and the controller failure result. Full terminal job log is also preserved. |

## Cause and local correction

The pinned producer manifest has903 entries:902 paths relative to the package root and the root directory itself keyed btx-0.34.16. Our fixture joined every key under the extracted root. Its root entry therefore became a duplicate nonexistent child. This was an orchestration mistake, not a BTX or archive defect. The new local accept.py removes and separately verifies/restores that root entry before comparing the remaining child inventory. Original digests, file bytes, modes and link checks remain required.

Source review also identified a later fixture interaction before spending another hosted attempt: upstream install staging uses cp -RP, which respects umask. Our adapter had selected077 while asserting archive0755/0644 modes. The local adapter now uses022 for that staging operation inside the enclosing0700 private runtime. No upstream installer/product code is changed; the enclosing parent remains inaccessible to other users.

## Local synthetic qualification — distinct from Ubuntu acceptance

The small regression in fixture-repair/test_fixture.py uses generated tiny archives and temporary fake version probes that only exit0. It uses no retained BTX archive, real BTX executable, wallet, key, coins, network or build. On local macOS ARM64/Python3.11.14:

- The two selected original-fixture cases reproduce duplicate-root FileNotFoundError and copied-directory0700 versus expected0755 failure.
- All four corrected cases pass: actual producer root/relative-key shape with hardlink under private077 mask; manifest file-byte mismatch still refused; root-mode mismatch still refused; staged payload modes retained while the outer temporary parent stays0700.

These are fixture regressions on Mac with Python3.11, not Ubuntu/Python3.12, real archive, installed-app or lifecycle qualification. The hosted104second attempt did not execute the local corrections. Logs, originals, patches, manifests and independent review remain in fixture-repair/. No next remote commit/dispatch was made.

## Resource state and next step

Private hosted runtime was removed with no containment signals or survivors; the job is terminal. First failed run44191690985 and second failed run44193516952 remain separate immutable evidence. Session1SwapNet and Session2ModelNet work and their mutable resources were untouched. No peer messages, real-wallet access, rebuild or upstream publication occurred.

Next useful step: after authorization, one bounded no-build run with the same archive, corrected admission/adapter and unchanged acceptance requirements, refreshing ref/bookings/artifact and exact payload identities first. No automatic third attempt. Actual Qt/Atlas/native local connection/restart/cleanup results are still required before a desktop handoff.
