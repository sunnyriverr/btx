# #905 Linux native review and Cancel observations

Credit: repch1c authored #905; Numair incorporated it into release-0.34.17. This check follows JPP’s platform-coverage work.

Tested source: `7d65025bb3bff27e4f6c2fdc95f33e4b859a2df5`, with neuronlab.rs equal to PR #905 head `aaab62ae140f522fcc480a4d1a3f55c7b2586afd`. Reused Atlas ELF SHA-256: `921505f2b333b0dfa5cddccf668544d6f800fefeabc445f735ac89c4b06e0d9c`. No rebuild.

[Run 44999566294](https://github.com/sunnyriverr/btx/actions/runs/44999566294) used packet `08ab19421183cbf6dc1b8c8d823708d7cc9991ee`, Ubuntu 22.04 x86-64, WebKitGTK 2.50.4 and Openbox/Xvfb at 1440×1000. The worker supplied explicitly synthetic, read-only presentation data.

The native review displayed the complete expected request, matching request SHA-256, 20 operators, a compact preview marked as truncated, and matching operator SHA-256. Both buttons were fully visible. Cancel returned successfully; a subsequent capture shows the dialog gone and Atlas reporting cancellation. The final worker log contains only reads. Four screenshots were visually reviewed and both digests independently recomputed. See evidence-audit.json and observed-result.json.

**CI failed; the original automated result remains NOT_QUALIFIED.** The dialog-disappearance wait started after Cancel and failed on X11 BadWindow. Later cancellation/stability, log-equality and final source/ELF hash checks were not completed. The observed result does not replace those checks. The file named failure-ui.png is the post-Cancel capture from that observer failure.

Cleanup passed: two adopted helpers were reaped, no owned processes remained, and private application data, the restored binary and portal directories were removed. This covers the observed TERM/reaping path, not KILL, interruption or normal window-close behavior.

Not qualified: real profile signatures, scientific/model execution, activation, Windows/macOS, high DPI, other resolutions or the full release. No wallet or production access. No product patch is supplied.

Request SHA-256: `6f08833ca04ce4c0c92cf7b60097648f1daac0ebec38e9a92492f8d64dd66ec1`.

Operators SHA-256: `44679de65f9259a673163d56934fc8c31cadd95f47ee062bebe5c64bda083eb5`.

The complete producer ZIP is 522,102 bytes, SHA-256 `6f2e6223acbddfb8860f1d89d37b7f754628f66232fe23807dc50c2f101d2dd6`. All 20 members were independently verified. MANIFEST.json records individual file hashes. Original failed qualification records are preserved alongside this scoped evidence review.
