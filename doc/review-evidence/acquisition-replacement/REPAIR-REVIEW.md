# Acquisition replacement repair — source review

Reviewed final `repair/src/modelnet/package_execute.cpp` against the recorded current baseline. Source review only; no independent execution or platform qualification.

No blocking defect identified in the scoped regular-file replacement change.

- The stale destination survives stage creation, short/error writes, stage hash refusal and rename failure. Publication happens only after the staged bytes hash to the authoritative expected digest. The new-file exclusive-write path stays unchanged.
- The sibling name is bounded and created through the existing exclusive/no-follow writer. Collisions are retried at most 16 times; unsuccessful stage writes clean themselves, and later refusals/rename errors explicitly discard the stage. Successful rename consumes it. Parent and destination symlink checks retain the prior boundary immediately before publication; this does not solve pre-existing hostile concurrent-directory replacement races.
- `fs::PathFromString` correctly adapts the generated name to BTX's path type. `std::filesystem::rename` is already the mechanism used by upstream `RenameOver`; no new platform-specific API or random dependency is added. Native Linux/Windows behavior is not established by this read.
- The maintained controller now requires original-byte preservation on the short-write case while continuing to test retry and cache reuse. It also checks missing/wrong-source preservation, fresh output, symlink refusal, credit release, and leftover staging files. This is a useful exact-before/after test rather than a source-opinion-only handoff.
- No fsync/directory-sync is added. Do not claim power-loss durability or process-crash cleanup: a crash can leave an unreferenced sibling stage. The bounded fault under investigation is a completed acquisition call returning failure after a real short write.

A later publication should keep the actual C++ API/component, macOS and empty-resource-ID-plan limits explicit. A rename-failure injection or native Windows check would strengthen those distinct boundaries but is not evidence the reproduced short-write repair is incorrect.
