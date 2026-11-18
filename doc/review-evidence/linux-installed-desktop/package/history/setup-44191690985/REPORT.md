# Installed desktop attempt — setup blocked, no BTX launch

18 November2026 Brisbane. [Run44191690985](https://github.com/sunnyriverr/btx/actions/runs/44191690985), attempt1, exact control286ec834c657ad855d45411c46b20f3866c439da, isolated fork branch codex/ci-session3-installed-desktop-074. One Ubuntu24.04 x86_64 attempt; no rebuild. The terminal workflow result is **failure**, not desktop acceptance.

## Actual result

| Gate | Observed result |
| --- | --- |
| Prepared input identity | All12 prepared source/configuration/producer-record hashes match locally. Four Python files parse without importing; six workflow shell blocks plus installer shell parse. All20 remote published input/doc blobs and modes match exact local bytes. |
| Runner/authorization gate | Passed on Ubuntu24.04 x86_64. |
| Retained artifact | Metadata ID14319148652/run44063898937/control3145c20f/digest/size/unexpired checks passed. Complete173,356,636B ZIP download and SHA256d9f58d9623a3e6d13b15b9e67ba2c2b16bb9b574985bbc9dcd69c4aed3daa664 check passed on the runner. |
| Host dependencies | Failed with apt exit100 before installation/desktop driver. Signed Ubuntu indexes downloaded successfully from mirrors.edge.kernel.org. Package downloads then failed: first IPv4 connection to142.0.200.124 timed out; IPv6 endpoint reported Network is unreachable. The underlying network change is not established. |
| Installer/inner archive/Qt/Atlas/lifecycle | Workflow step skipped. No new inner-tar hash check, extraction, version probe, daemon/application launch, GUI observation, helper/guard boot or restart ran. |
| Completeness collector | Correctly failed because prerequisite=failure and desktop=skipped. No acceptance result JSON or screenshot exists for this attempt. |
| Evidence upload | Passed. Artifact14376323226,638B ZIP, SHA256b3d595fdd0b08979bfdee1a24270768c90af681111d4503366e5acbea09e6d47 independently downloaded and verified. It contains only preflight-records/artifact-metadata.json, as expected after setup stopped. |

This is an external package-download/setup failure. It is not evidence of a BTX defect, a failing installed app or a passing desktop. The previous packaging result and historical Session2 acceptance remain separate evidence with their original identities. No current-release/0.34.17 qualification follows.

## Cause in our orchestration and local correction

The inherited mirror selection stopped after a successful signed-index update. A later package-pool connection failure therefore bypassed the other mirrors. The local correction in local-repair/prerequisites.sh and workflow.patch selects a mirror only after the complete same dependency set has downloaded, then installs from the APT cache with --no-download. Signed-index/package verification remains enabled. The420second shared fetch budget plus90second offline-install cap fits the existing nine-minute workflow step; no GUI assertions, archive/source pins, runtime scripts, packages, build steps or execution limits are relaxed.

The corrected workflow and adjusted payload manifests are **local and unexecuted**. Shell parsing alone passes; it does not demonstrate successful dependency installation or desktop acceptance. No second dispatch, remote follow-up commit or upstream PR/comment was made. Review notes and exact hashes accompany this report.

## Evidence and resource state

Primary evidence: job134422475370.log, job-terminal.json, run-terminal.json, artifacts-terminal.json, remote-payload-verification.json, dispatch-receipt.json and the verified638B record ZIP. Full downloaded candidate bytes remained on the disposable hosted runner; no candidate archive was downloaded to the Mac in this step. Private runtime was never created because the controller was skipped. No BTX processes required cleanup. The hosted job is terminal and its ref/runtime/workflow-routing execution bookings are released; task/root and prepared-fixture ownership remain.

Session1SwapNet and Session2ModelNet work remain separate. No peer messages, mutable peer cache changes, real-wallet/key access, coin movement, production changes, signing or upstream publication occurred. The authorized fork workflow and setup logs are public; new correction remains local.

Next useful step: one explicitly authorized corrected no-build Ubuntu attempt using the same retained artifact and unchanged acceptance assertions, after rechecking artifact/ref/bookings and corrected payload identity. Preserve this failed attempt and do not count it toward desktop coverage. The no-automatic-retry limit remains in effect.
