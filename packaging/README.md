# Current-source desktop package helper — preparation only

`package_candidate.package(w, inputs, python, run, records, tick=...) -> dict` is intended
for the future authorized controller stage after its bounded 17-target build.
It has not been run, syntax checked, imported, configured, or tested during this
source-only preparation. No build, package, native product probe, download, CI,
post, installation, wallet or GUI action was performed.

The controller must provide an absolute workspace Path, the flat pinned input
mapping, the exact selected Python executable, its cancellable/logging `run`
function returning stdout text, and a build-records output Path. The controller
must supply its deadline/capacity `tick` callback. The helper calls it around
commands and archive operations, per archive member, and for every 1 MiB block
while copying or hashing inputs/archive payloads, preserving retention time
during in-process work as well as subprocesses. The optional no-op default is
for interface compatibility, not the production controller configuration.
The controller
retains responsibility for build admission, fresh resource/target checks,
dependency identity, source trust, capacity monitoring, complete process-group
cancellation and timely verified checkpoint retention on failure or success.
The helper cannot independently prove its caller actually compiled C++ inputs;
the controller's successful exact-target build receipt supplies that evidence.

Expected mapping keys are `source`, `workspace`, `targets`, `atlas_source`,
`atlas_tree`, `atlas_archive_sha256`, `atlas_binary_sha256`, `atlas_artifact`,
`atlas_run` and `atlas_fixture`. All source/component pins are independently
checked against constants. Product source is `w/product`, C++ binaries are
`w/gui-pilot-runtime/qtbuild/bin`, and old Atlas inputs are `w/atlas-input`.

`atlas-input/provenance.json` must be the fetcher's normalized envelope:
`artifact_id`, `run_id`, `producer_head_sha`, `source_sha`, `outer_sha256`,
`archive_sha256`, `atlas_binary_sha256`, `atlas_tree_sha`, and
`verified_original_provenance` containing the original complete provenance
object. That original object must retain `source`,
`candidate_archive_sha256`, and
`candidate_files["libexec/btx-atlas.real"].sha256` with their verified values.
The fetcher is responsible for verifying full remote metadata, outer ZIP,
inner archive and original provenance before emitting this envelope. This is
a trust boundary, not a cryptographic signature created by the helper.

Only the old verified regular Atlas ELF is copied into the current binary
input directory. No old wrappers, libraries or mutable Rust cache are used.
Whole `HEAD:gui/atlas` tree identity and a clean Atlas worktree (including
ignored/untracked additions) are required. The accepted full source head and
tracked/untracked worktree are also checked. The helper rejects release-gate
environment overrides and preexisting Atlas/output paths instead of reusing
stale package state.

The current unmodified native packager receives `--python` pointing to the
selected interpreter, `--require-gui` and `--require-model-helpers`. The helper
separately requires all 18 wrappers and real payloads, including Atlas, and
the regular/hardlinked guard sibling. Current packager all-ELF GLIBC 2.38,
GLIBCXX, CXXABI, GCC, OpenSSL and reachability gates remain in force. The
standalone current archive verifier uses `--no-launch` with every model helper
required. No floor/component override or wallet derivation option is used.

Native package/probe subprocesses share a 900-second budget: host runtime
installation up to 180 seconds, before/after package inventories up to 15 seconds
each, host Atlas ldd closure up to 30 seconds, packager up to 600 seconds, and
static archive verifier up to 180 seconds. These are individual maxima; each
command receives at most the remaining shared budget. The packager itself runs `btxd -version` and Python import
and bundled-runtime probes. Its execution therefore requires future explicit
package/probe authority even though standalone verification has no launch.

GTK/WebKit and display services remain host dependencies by the current source
contract. The helper requires the verified Atlas input's builder-host `ldd`
closure and records its command log. After the C++ build, within the packaging
phase, it installs the exact Ubuntu 22.04 runtime package list
`libwebkit2gtk-4.1-0`, `libgtk-3-0`, `libayatana-appindicator3-1`,
`librsvg2-2`, and `libxdo3`, with apt dependency closure. This uses the setup's
current package cache, no `apt update`, `--no-install-recommends`,
`--no-upgrade`, and `DEBIAN_FRONTEND=noninteractive`. It captures full installed
package/version/status inventories before and after, then aborts if any
previously installed package version changed or was removed. Newly installed
package versions are recorded as packaging-host inputs, separate from the
unchanged compiled-input baseline. No GTK/WebKit development
packages or Rust compilation are required. This host check does not prove
the final archive launches on Ubuntu 24.04. Failure stops for an explicit
dependency decision; it never starts an automatic Rust build.

The archive manifest hashes every regular payload, legitimate hardlink payload
and link text without extracting members. It validates bounded canonical
paths, one expected release root, special modes/types, symlink ancestors and
ordered regular hardlink targets first. The shipping verifier retains its own
independent extraction and member checks. The guard's two real names may be
regular/hardlinked in either tar writer order; their byte digests must match.
Per-component records distinguish prepackage inputs, final real bytes and
wrapper bytes; RUNPATH edits may legitimately change Atlas's final digest.

The returned verdict is a static package-gate result with runtime qualification
pending. It is neither a sealed archive claim nor a GUI, wallet, daemon service
integration, restart, installed-tree or official-release acceptance pass.
