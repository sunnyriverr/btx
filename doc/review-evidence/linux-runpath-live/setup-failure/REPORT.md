# Live-module qualification — setup failure

Run [44259884679](https://github.com/sunnyriverr/btx/actions/runs/44259884679), exact fork commit `c70f95148c0ed37c4b8ea8c6d3451fbe8f2a256d`, completed with failure. All ten remote input files were byte-checked before dispatch. Upstream a97 and isolated fork de48 heads were unchanged; peer statuses and bookings showed no overlapping mutable work.

Ubuntu22.04 and minimum CMake setup, compiler prerequisites and pinned modern CMake setup succeeded. The controller stopped at its first input-hash admission because sparse checkout omitted `.github/workflows/linux-replacement-pilot.yml`. The file exists in the commit but was not selected onto the runner. The manifest correctly refused the missing input. This is our workflow setup defect, not a product-test failure.

**Zero CTest contexts and zero regression cases executed.** The controller summary contains empty contexts/commands. No new before/after, default-suite, cleanup or helper qualification is established. Earlier frozen native evidence is unchanged.

Artifact14406889235 is7148bytes; its downloaded ZIP hash matches GitHub's SHA256 digest `be0bba9418805425147e9cd8bc8a8c8ba32db1d2addd51396dcd5ed58a4f7a00`. All19ZIP entries extracted safely; raw logs and summary preserved. No automatic retry. One authorized dispatch consumed.

Local-only correction adds the exact workflow path to sparse checkout and updates its hash in INPUTS.json; other eight payload files are unchanged. Corrected payload hashes, YAML and three shell-block syntax checks pass. This correction remains unexecuted/unpublished. See [corrected preparation](../corrected-preparation/README.md). Next useful action is one explicitly authorized corrected attempt with unchanged limits/matrix after fresh head and resource admission.

No upstream post, wallet access, BTX build or peer mutation. Release temporary CI/ref/workflow bookings; retain own task/root/product components. Lesson: validate that every admission-manifest path is selected by sparse checkout; remote blob existence alone is insufficient.
