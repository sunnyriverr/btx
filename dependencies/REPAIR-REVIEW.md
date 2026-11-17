# Dependency repair source review — 17 November 2026

Scope: local source repair only under `preflight/payload/dependencies/`. No script, syntax check, install, Python archive/wheel download, configure, build, native execution, test, dispatch or publication was performed. Session 2 producer files were read only. The parent Session 3 reservation `97bfd688-5c70-4545-8e98-e699c26dd5e2` covers this delegated directory; no shared execution resource was used.

## Observed defect and historical comparison

- `../../execution/corrected-configure.log` reports missing `OPENGL_INCLUDE_DIR`, then missing `WrapOpenGL`; `Qt6Gui` and `Qt6Widgets` are rejected and generation fails because `Qt6::Widgets` is absent. The log nevertheless reports Python 3.12.16 `Interpreter Development Development.Module Development.Embed`. This is a prerequisite failure, not evidence that BTX GUI source is broken.
- Read-only ZIP member `../../execution/records-14308228510.zip!preflight-records/installed-packages.log` contains `libglx-dev:amd64`, `libopengl-dev:amd64` and the required Qt development packages, but no `libgl-dev` entry. Both existing GL development packages are version `1.4.0-1`.
- Successful Session 2 producer `work/btx-lanes/session-2/linux-replacement-candidate/producer/run-43428864330/pilot-records/installed-packages.log:226` contains `libgl-dev:amd64 1.4.0-1`. Its `CMakeCache.txt:506` resolves `OPENGL_INCLUDE_DIR` to `/usr/include`, and `:1186` records `WrapOpenGL` as `[ON]`. Original `producer/setup.sh` installs the broader GTK/WebKit development closure. The narrow missing OpenGL header dependency is restored explicitly; this does not require restoring that larger closure.

## Source changes

`setup.sh` adds direct `libgl-dev`, then immediately requires installed `libgl-dev:amd64`, `/usr/include/GL/gl.h` and that exact package ownership before Python bootstrap or project configure can begin. It retains package version, owner and header digest logs, includes apt policy, and adds package/header identity to the dependency receipt. This uses no compilation. The presence/owner check must still be qualified in a future authorized Ubuntu run; it does not certify CMake target resolution.

`input-manifest.json` records the explicit prerequisite and observed historical version. The existing policy remains: only the already selected GCC/Qt baseline is exactly apt pinned; other installed versions are recorded and no complete reproducibility claim is added. `README.md` explains the change, prerequisite-only evidence and execution limits. This note is source review, not a pass receipt.

## Python bootstrap limitation retained

Read-only ZIP member `preflight-records/dependencies-setup.log:1660–1670` shows the archive installer fetching pip `26.3` and replacing bundled pip `25.0.1`, before the five hash-locked wheel installations. The source [actions/python-versions nix installer template](https://github.com/actions/python-versions/blob/main/installers/nix-setup-template.sh), read as public source metadata on 17 November 2026, performs an unconditional pip upgrade/reinstall and exposes no skip flag. That mutable template is supporting evidence only, not proof of the exact archive's installer bytes.

No verified installer skip semantics or exact archived setup source is available in the retained inputs. A generic no-index setting could fail an unconditional reinstall; blind modification of a downloaded script would not establish a robust supported installer change. Therefore no speculative bootstrap fix was made. The exact Python archive SHA256 and five existing wheel pins remain unchanged. The manifest and README disclose the bootstrap gap, and the future receipt records the observed pip version under `pip_bootstrap`. Fully pinned/network-free bootstrap remains unresolved; its next useful trigger is separately authorized inspection of the exact archive installer and a verified compatible skip or pinned bootstrap mechanism.

## Verdict and remaining action

The revised source addresses the observed missing OpenGL header input and fails earlier if the explicit package/header contract is unmet. This review does not claim a passing setup or configure, a complete dependency closure, reusable old C++ objects, or a pinned pip bootstrap. Parent payload-manifest regeneration is still required after integration. No run is authorized by this note. No Session 2 files, controller, workflow, product code or parent reports were changed.
