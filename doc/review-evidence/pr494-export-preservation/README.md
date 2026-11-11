# Preserve the old export on short writes

An injected short write removed the existing model link and bundle before the fix. With the fix, both old exports and their permissions were preserved, a failed first export left no file, and healthy retries produced the expected bytes. Both writers still refused symlinks.

Ubuntu 22.04 helper RPC with a per-process file-size limit. Physical disk-full, abrupt shutdown and native Windows coverage are outside this run.



The matched run uses the verified `dac9aee5` checkpoint and GCC 11.4. Changed translation units were compiled at `-O0` in both variants. The patch builds on repch1c’s original changes.

- Author head `3ba462b19c2b2f5b33fb4ec8d5aa1e021da074b1`
- Tested product tree `97e323b10aa935161536b22bb76f47f3005d5814`
- [Cherry-pickable fix](https://github.com/sunnyriverr/btx/commit/2d501945219231400ba6d3c45b959c2f3a81d9d3)
- [Executed CI and per-PR records](https://github.com/sunnyriverr/btx/actions/runs/43001503550)
- [Pinned fixture and build recipe](https://github.com/sunnyriverr/btx/tree/91a0c11d90e95f83c513ede59b747ff2d98c1920)
