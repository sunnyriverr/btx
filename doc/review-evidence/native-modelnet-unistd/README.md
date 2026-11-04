# Native Modelnet direct-header prerequisite

This branch pairs product commit `487a69f035190526793c2b3dec6df9e0110b9fc3` with the existing native before/after evidence. The product is based on accepted swarm `2cdff4fc38571df6996d88018bf0ce4d0077b755`.

- [Measured results and limits](REPORT.md)
- [Exact component reproduction recipe](REPRODUCE.md)
- [Source identities](closure.json), [native result](result.json), [artifact verification](artifact-verification.json)
- [Independent artifact review](review-RESULTS.md)

The records were captured before publication. Their references to a local/private product or pending handoff describe that measurement/preparation state, not the delivery status of the PR linking this branch. No additional execution was performed while publishing.

The same two actual production files fail before and compile after under MSVC and clang-cl; ten direct-header controls pass per compiler. This is a bounded CMake component comparison. It does not qualify the stock-root build, complete Modelnet library/helper, full node or Windows test_btx. OpenSSL setup, other native portability/unit prerequisites and plain-cl arithmetic remain outside the result. CMake route preservation for MinGW/Unix was checked without native execution on those platforms.

Original missing-header report: repch1c in issue #356. Jpp-matata's Windows build/testing coordination and complementary coverage informed the scope. Existing adapter authorship is preserved in the parent history.
