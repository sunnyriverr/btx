# Linux cgroup v2 mining pressure for #912

**Result:** With identical host RAM and about 5% host swap free, the unchanged governor denied the mining permit in a healthy limited cgroup with zero swap use. The candidate allowed it. The healthy host-swap control allowed mining on both builds.

- **Source:** `2c4da891f0089ebc0fb082e65d03a4efda4488a3`, and that same source plus [the tested patch](fix.patch).
- **Platform:** Alpine Linux aarch64, Linux 6.12.81, GCC 14.2.0.
- **Entry points:** [component build](build.sh), [paired observation](observe.sh), [saved-results validator](validate.py).
- **Evidence:** [validated cases](result.json), [raw observations](observation.log), [build and binary hashes](build.log), [input hashes](inputs.json).

Both binaries use the same consumer to call production `SampleHostSignals()`, `Observe()` and `Permit(MINING)`. The consumer links a test logging sink. The main pair used real cgroup v2 limits and usage, and a private mount supplied host memory readings. The pressure controls supplied deterministic readings at the controller-file boundary. Ten cases per build checked healthy operation, finite and zero swap limits, container RAM and swap pressure, a finite ancestor, unlimited swap, host-only fallback, and host RAM pressure.

To reconstruct, use a disposable Linux VM with GCC, a cgroup v2 memory controller, and permission to create a private mount namespace. Stage the inputs listed in `inputs.json` from the pinned source and this directory. Keep the original translation unit at `src/node/resource_governor.cpp`. Apply the patch to a separate copy and place that output at `candidate/resource_governor.cpp`. In the staged directory run `timeout 90 sh build.sh`, then `sudo timeout 60 unshare -m sh observe.sh > observation.log` and `python3 validate.py`. The observation uses a temporary cgroup and private file mounts. Use the recipe only on an isolated test instance.

This was a native Linux component comparison. No full daemon, GPU mining, physical bare-metal host, cgroup v1 or other platforms were run. The root-cgroup cases exercised the host fallback. The scoped candidate uses a verified process membership under the standard cgroup v2 mount and accounts for visible ancestors.

Credit [Jarek](https://github.com/jarekpiot) for the report and the cgroup v2 direction. [Issue #912](https://github.com/btxchain/btx/issues/912)
