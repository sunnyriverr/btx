# Report shutdown interruption during import rescan

With a simulated shutdown at the scan boundary, the original import RPC logic selected success. The fixed logic selected RPC error −1. Normal completion, user abort and unreadable-block controls kept their existing outcomes.

The changed wallet translation units compiled on Ubuntu 22.04. The before/after result comes from an exact-code component test with a simulated chain. HTTP delivery during actual shutdown was not tested.

The shared workflow is marked failed because the separate #494 bundle fixture stopped at request validation. The published #502 results are in its own successful section of the artifact.

The matched run uses the verified `dac9aee5` checkpoint and GCC 11.4. Changed translation units were compiled at `-O0` in both variants. The patch builds on repch1c’s original changes.

- Author head `5ef5032877ce3d4d72000f3640da48edce5dda35`
- Tested product tree `381533306ba3ae95eb5df83aa64e1f198ee64f62`
- [Cherry-pickable fix](https://github.com/sunnyriverr/btx/commit/37fbefc7ce3b07c486f4f0a8965991389511e54f)
- [Executed CI and per-PR records](https://github.com/sunnyriverr/btx/actions/runs/43000822596)
- [Pinned fixture and build recipe](https://github.com/sunnyriverr/btx/tree/8bab7fdc0f8ff360b0e0e74b84eb2a60a0c41d5c)
