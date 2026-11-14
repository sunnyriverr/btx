# Independent bounded repair review

Scope: compared only source/candidate `contrib/swapnet/swapnet/adapters.py`, `swapnet/drivers.py`, and `tests/test_psbt_version.py`. Read-only source review; no tests, native processes, peer resources, or publication performed. Native and Python test outcomes supplied by the owner are corroborating evidence, not independently rerun results.

Verdict: no demonstrated blocking regression in the reviewed repair. Core30 native compatibility remains an owner validation gate until its result is available.

- `adapters.py:17-25` uses a single funding call, selects Core32's positional PSBT version argument from the wallet help contract, and retains five arguments for older Bitcoin RPCs. BTX driver calls do not probe Bitcoin argument contracts. The bounded tests cover both help shapes and no retry of a funding rejection.
- `drivers.py:118-145` requests funding without wallet locking and completes fee, input, output and plan validation before explicit acquisition. This removes the baseline fee/validation-failure wallet-lock leak.
- `drivers.py:145-162` starts cleanup only after successful explicit acquisition and releases only that input list. With native all-input validation before lock mutation, an already-locked-input rejection cannot justify unlocking someone else's lock. The owner's reported pre-existing-lock preservation test supports this boundary; native implementation atomicity itself was outside the permitted file comparison.
- `drivers.py:147-154` signs and validates the final transaction before storing the reservation. Thus ordinary signing/decoding failures leave neither a newly stored reservation nor acquired wallet locks, and a store exception triggers wallet cleanup. This conclusion assumes the store's existing transaction contract does not commit partial reservation state and then raise; that implementation was outside this bounded review.

Residual limits, not newly demonstrated regressions:

- A lost RPC response after native lock acquisition, process termination, or a failed cleanup RPC can leave wallet locks requiring recovery. Baseline funding-with-locking had the same ambiguous-response/crash class. Do not describe this repair as crash-atomic or as covering all failure outcomes.
- Exceptions after `prepare_funding` successfully returns lie outside its cleanup scope. Durable preparation/raw transaction persistence and later-stage rollback still require the existing coordinator/recovery contract; this patch does not establish that contract.
- Both acquisition and cleanup use batch RPC semantics. The useful remaining focused check is a mixed batch containing one previously locked input and one unlocked input, asserting acquisition fails without changing either lock state. This is a qualification suggestion, not evidence of a defect.

No source changes requested by this bounded review. Preserve the supplied fee/sign/store-failure and healthy-retry native evidence alongside the final Core30 compatibility receipt.
