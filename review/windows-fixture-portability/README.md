# Windows unit fixture portability review

**Fix series a75dc8f60207 targets accepted swarm666673a3. PR #411 remains an explicit integration prerequisite, excluded from this PR's diff.**

- Code: `codex/fix-windows-fixture-series`, five logical fixture commits on `666673a3153225ba264c7870e0e82e354df86765`; compare that base to this head for the 50-file proposal.
- Dependency: PR #411 at `362c36b2fda0f73741c06c4bcb090153fea38a08` is still open/unmerged. Applying it with this series gives exact tested source tree `d860c05655a867235ca38e6e78d5b2431cc24a8f`. Its capability_runtime.cpp change is not resubmitted here.
- Latest native evidence: the same eleven generated compiler targets fail before/pass after; thirteen selected maintained cases pass, 341 assertions. Earlier campaigns are recorded separately below.
- Profile: Server2025 x64, clang-cl20.1.8, MSVC14.51.36231 libraries and SDK10.0.26100.0. Full test_btx, stock-source, Windows11/full-cl.exe and release qualification remain open.

Use the code branch for review/builds with the stated prerequisite. The evidence branch adds review records and retains the source-identical prepared integration b69f04b5 as historical provenance; it is not the PR branch. [Publication source map](publication-source-map.json) proves the exact dependency/source mapping and preserves original test/cache identities.

## Review order and source mapping

| Commit | Coherent change | Dependency |
| --- | --- | --- |
| c6fece258ce8 | Portable environment mutations in 27 fixture/helper files | PR #411 is the recorded integration base; environment helper provided here |
| f14bbc996155 | Scoped Windows OPAQUE macro handling in 10 fixture/helper files | Independent of the environment helper |
| 12a4d623a1a4 | Three native fixture contracts: supported refusal, qualification setup and exact bytes | Uses the environment helper; retains POSIX behavior and safety checks |
| b06e63f1272c | Canonical cloud GetObject header/callers, exact byte fixtures and supported synthetic ENV credentials | Uses environment helper; public header and three callers kept together |
| a75dc8f60207 | Real native PID helper and nine filesystem consumers | Helper and all 10 call sites included together |

[Code manifest](code-manifest.json), [stored commit/credit facts](git-facts.json), [human-readable commit messages](git-show.txt) and [independent package review](review/code-series.md) document the exact mapping. Original authors/dates and the Windows prerequisite audit credit to repch1c and Jpp-matata are preserved. All original mapped commits were authored by Sunny River; no coauthor trailers were removed or invented.

The publication branch reparents the prepared five-commit fixture series onto accepted 666, leaving #411 separate. Fixture source blobs, authors, author dates and messages are unchanged. The only full-tree difference from the previously tested integration is the explicitly excluded #411 file; applying that exact prerequisite restores tree d860c056, matching executed473a2a0b. No build or test was repeated for this history-only packaging. Original binaries and cache/build-info retain their actually executed source identities, not the new publication hash. New intermediate commits were not separately executed.

The original [code manifest](code-manifest.json) and [stored commit facts](git-facts.json) describe prepared integration b69f04b5; the publication map identifies the current clean branch. [Package review](review/code-series.md) is source/credit review, not independent platform execution.

## Evidence matrix

| Campaign | Actual source | Observed result | Honest boundary |
| --- | --- | --- | --- |
| [Earlier prerequisite campaign](earlier/verification.json), native41975209022 | bc85ca3460bb |39 recorded compiler failures corrected; separate real environment controls on MSVC and clang-cl | Direct selected targets/helper tests; four adjacent blockers remained then |
| [Four fixture corrections](four/completion.json), native41983219088/41984877146/41985603550 |666302d0,35e1d08f,8a642b1e | Four selected TUs compile/link; ten selected cases, 134 assertions across these recorded revisions | Not all ten cases from a single final binary; corrected CRLF and credential-source pilots retained |
| [Full maintained-target attempt](full-unit/verification.json), native41990045506 |8a642b1e |426additional cached objects; stops at retrieval fixture missing unistd.h | Unit executable not linked or run; initial root-bootstrap recipe mistake disclosed in verification |
| [Grouped diagnostic](baseline/verification.json), native41994623193 |8a642b1e |21 same-generated target failures:19 unistd / 2 SDK GetObject collisions | Expected diagnostic failures, not a candidate pass; earlier retrieval failure reused |
| [Latest focused qualification](latest/verification.json), native41997202444 |473a2a0b | Same eleven targets compile/link in 22.17s; 13 cases, 341 assertions pass | Explicit 15-object component using maintained main/library closure; original full target unchanged |
| [Mac PID helper control](mac/receipt.json) |473a2a0b | Native type / positive PID / getpid equality pass | New helper only; full POSIX fixtures not rerun |

Readable original logs are under [logs](logs/); the latest [run record](latest/run-record.json) contains executed commands, exact compile entries, library/symbol checks, cases, cleanup and hashes. [Manifest](manifest.json) verifies copied evidence and identifies immutable original CI/artifacts. Primary review does not require opening an archive. Large full-source catalogs/checkpoints remain in the recorded hash-verified CI artifacts and local retained records; the hosted artifact retention is 14 days.

The latest R2 case retains exact Windows file-permission refusal and then performs 41 real assertions through the supported synthetic ENV route. Store2 verifies valid cloud-fill, 10 assertions and corrupt-byte refusal, 13 assertions. Canonical bitcoin_modelnet library SHA256 remains `4c924f0731642e0b8aedece02ba8a3229a59b254c0da20637aaea39db5fb529c`. There are no real cloud credentials or live-cloud tests. Other PATH-backed R2 cases remain unqualified.

## Limits and the next decision

Ten other grouped socket/process/security/SDK fixtures plus the earlier retrieval fixture remain unchanged and unresolved. No global compatibility shim, disabled safety assertion or pruned full test list was used. The latest component left no scratch paths or owned children; original logs show no forced cleanup. Source equality does not qualify every case in the newly grouped files or all combinations of earlier tests.

Review the portability series and its explicit #411 prerequisite. Accepted666 and unchanged open #411 were rechecked before submission. If #411 changes or lands differently, inspect the material delta before updating this series. The full native node/unit gate remains a separate acceptance task; do not ask for #356 closure from these results.

[Executed workflow and reconstruction limits](REPRODUCING.md). This evidence records existing runs; publication did not repeat a test campaign.
