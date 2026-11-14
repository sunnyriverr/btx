# Local release signer/recovery checks

At BTX candidate `a5d1637facc925ff176507fae87fc2042940829d`, 41 maintained checks and 14 supplemental checks passed on macOS 26.5.1 arm64 / Apple Python 3.9.6. Three separate sensitivity checks detected deliberately removed fingerprint matching, KeyboardInterrupt cleanup and draft-first staging. No product change is proposed.

## Run

From this evidence directory:

```sh
python3 -B no-key-tests/run_all.py
```

The runner exits nonzero for failed tests or worker-guard violations. No installed GPG or GitHub credentials are needed. This exact packaged entry point was executed locally; see [results](no-key-tests/results.json). [Source/test identities](no-key-tests/provenance.json) identify the unchanged source snapshot and local supplemental tests. The source files retain the upstream license; see [COPYING](COPYING).

| Selection | Passed |
| --- | ---: |
| Maintained cut / sign / publish suites | 6 / 2 / 29 |
| Maintained collector signing / installer signature selections | 2 / 2 |
| Supplemental signer validation / signing recovery / publishing recovery / installer characterization | 5 / 4 / 3 / 2 |
| Separate broken-control sensitivity checks | 3 |

Logs: [cut](no-key-tests/cut-release.log), [sign](no-key-tests/sign-release.log), [publish](no-key-tests/publish-release.log), [collector](no-key-tests/collector-signing.log), [installer](no-key-tests/installer-signature.log), [supplemental](no-key-tests/new-contracts.log), [sensitivity](no-key-tests/broken-controls.log).

Catchable signing interruptions restore original bundle contents byte-for-byte and allow retry. With a simulated GitHub API, upload failures after accepting an asset and incomplete readback leave the release draft; retries complete before the final publish transition. Actual installer code accepts both simulated GPG-success identities, whereas strict publisher fingerprint mismatch rejects. That characterizes current behavior, not acceptance of a real unauthorized signature.

GPG and GitHub responses are mocked. Real hashing, bundle rollback, archive extraction and release orchestration run against small inert fixtures. No real signatures/uploads, abrupt process-kill/power-loss recovery, failed rollback writes, ambiguous final-publication responses, native BTX build or other OS qualification were tested. Workers recorded zero prohibited process/network/keyring attempts; the guard is scoped test instrumentation.

The publisher's independently pinned identity is explicit in [release automation docs](https://github.com/btxchain/btx/blob/a5d1637facc925ff176507fae87fc2042940829d/doc/btx-github-release-automation.md#local-release-validation). Reviewed installer docs require checksum/signature verification but do not explicitly define an installer signer allowlist. Clarify the intended consumer policy before proposing a product change. The [existing release-process request](https://github.com/btxchain/btx/pull/432#issuecomment-6881907467) remains distinct from this no-key campaign.
