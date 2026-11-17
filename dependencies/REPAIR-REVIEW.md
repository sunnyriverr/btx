# Historical dependency-repair evidence

The original configure-stage repair review remains unchanged at
[build-package dependency repair review](../../../../build-package/payload/dependencies/REPAIR-REVIEW.md).
That review describes historical execution and its original configure-only
recipe; its invalidation and tool-probe requirements do not describe this
packaging-only continuation.

The current adaptation is source-only and unexecuted. Its recipe preserves the
original apt/Python/wheel inputs and comparative dependency evidence while
removing compiler, CMake and Ninja invocations. It does not invalidate objects,
reconfigure or rebuild. The current interface and exact comparison contract are
in [README.md](README.md); original recipes and receipts stay immutable.
