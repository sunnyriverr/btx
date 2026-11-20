# SwapNet EVM transaction lookup response

Target base is release-0.34.17 at 4134c67f. This follows Jpp-matata’s request for driver error-path coverage.

On the base, the new cases found two failures. A non-object Ethereum lookup raised AttributeError. An empty object was treated as absence and reached broadcast. The fix keeps JSON null as the absence result, recognizes the original transaction by its hash, and treats unexpected results as a typed chain response error.

On macOS 26.5.1 ARM64 and Python 3.12.10, all 12 driver cases passed with this PR alone. The focused command was python -m pytest -q tests/test_driver_rpc_failures.py from contrib/swapnet. The tests use real drivers and a durable SQLite journal with simulated RPCs and transaction data. They verify retry after reopening and exactly one send. Four separate simulated checks exercised the withdrawal caller and retained its canonical finality check.

The full Python suite with this fix plus the separate startup and SQLite test changes passed 577 tests and 28 subtests. Native nodes and chains, Linux and Windows were outside these runs.

[Baseline result](baseline.txt) · [Isolated PR run](pr-only.txt) · [Withdrawal review](withdrawal.txt) · [Combined suite result](combined-suite.txt)
