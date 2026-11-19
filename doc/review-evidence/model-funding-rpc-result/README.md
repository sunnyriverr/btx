# Model funding wallet response regression

The same maintained wallet_modelnet_funding.py test failed on the baseline and passed with the nine optional string declarations. The test kept rpcdoccheck=1 and checked gettransaction, listtransactions and listsinceblock against the frozen values. It covered funding with and without a release reference, an ordinary transaction, and the existing claim and refund workflow.

The executed entry point was proposal/run_test.py in the [fork qualification run](https://github.com/sunnyriverr/btx/actions/runs/44424449598), at recipe commit 6b2c571899e304f123f3593148943de5f355a244. It used a retained Linux x86-64 Ubuntu 22.04 build at 371013d6 with an unrelated profile candidate. Six relevant source files matched the target a97af7b3. ModelNet was compiled in with the helper disabled for the explicit terms fixture. The checker and funding producer were unchanged between runs.

The native baseline exited 1 at the first funding query with nine undeclared result keys. The candidate exited 0 and the framework reported “Tests successful” after stopping the node. The workflow badge is red because a log collector expected “Test passed.” The saved exits and framework logs were verified offline, including negative checks for failure, skip and missing success markers.

See [verified result and artifact digest](result.json) and [selected framework log lines](framework-excerpts.txt). The linked run has the full qualification logs. This covers the maintained Linux regtest test with disposable funds and diagnostic MatMul settings. No other platform or full release suite was run.
