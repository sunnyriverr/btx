# #472 native Mac evidence

The same real-helper test failed all four regression assertions on
dac9aee53520bd49ed320ec7a49b9072fc7d88d9 and passed all four with the candidate. The product commit is
59419d53ebd9d9994f7947504a527b3c8157fb5c. Its four changed files match the verified candidate blobs in
the [source manifest](manifest.json).

[Native CI run](https://github.com/sunnyriverr/btx/actions/runs/42803621193) on macOS 15.8.2 arm64, disposable regtest.
The job uses the same real-helper test for the baseline and candidate,
then runs the maintained rpc_modelnet_wallet_restriction.py test against
the candidate node. The run record links the original artifacts and logs.

| Check | Baseline | Candidate |
| --- | --- | --- |
| Single release and fundable list for a caller with no wallet | Both expose the operator's 2,000,000-atom observation after the operator read | Both retain the public observation, including the nested list fields |
| Public list order and limit one | The funded release moves from second to first | The public order and first result stay stable. The operator still ranks the funded release first. |
| Valid wallet and operator views | 13 controls pass | The same 13 controls pass, including the funding wallet seeing its own funding. |

The maintained test also checks compatibility on the native candidate
node. A Unix-socket fixture simulates the older helper's
METHOD_NOT_FOUND response. For each read the node issues one scoped
request, returns the compatibility error and makes no unrestricted retry.
The fixture also verifies ordinary helper-error parity between callers.

Runtime coverage is for getmodelreleaseeconomics and getfundablemodels
on Mac regtest. The remaining mapped readers were reviewed in source.
The older-helper check uses a simulated response.

Credit to [repch1c](https://github.com/btxchain/btx/issues/472) for the report and original
real-helper reproducer, which informed this test and repair.
