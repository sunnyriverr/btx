# Reproduce the focused local helper comparison

No node, wallet, public peer, model execution or GPU is required. Native macOS comparison here used existing CMake helper libraries. build.py records the local cache paths and compiler flags and compiles only helper.cpp for each variant; its cache is not a portable clean build recipe. On another system, build btx-modeld from baseline swarm cbf65894 and from that same base plus candidate.patch using the repository's normal Modelnet build, then copy those binaries into baseline/btx-modeld and candidate/btx-modeld here. Verify their identities before interpreting results. binary-identities.json pins the two tested Mac binaries; for your own build, record your actual binary hashes there and retain exact source/build provenance.

```
python3 reproduce.py baseline
python3 reproduce.py candidate
python3 retention.py baseline
python3 retention.py candidate
```

The lifecycle script records FAIL/PASS in each *-result.json (it completes controls even when a behavioral check fails). Expect baseline FAIL on five local cleanup checks; candidate PASS on all17. Memory sequence expects RSS to grow with unique IDs on baseline and remain approximately flat on candidate. Do not treat one RSS sample as exact heap proof. Scripts create/remove private /tmp fixtures and terminate only the helper processes they launch. Keep at least1.25GiB free. Runtime retention guard stops above256MiB RSS.

preservation.cpp is a narrow extracted-function component test with adapters, separately documented in REPORT.md. It is not a remote-network test.
