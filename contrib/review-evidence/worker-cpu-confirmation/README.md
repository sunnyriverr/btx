# Worker CPU-confirmation test evidence

The code commit is identified in identity.json. The PR should contain only that test-file commit; this separate evidence branch carries the paired result, sanitized logs and limits.

On a matching CPU-only build of the code branch, run the native maintained cases:

```sh
/path/to/test_btx --run_test='matmul_verify_worker_tests/cpu_confirmation_pending*' --log_level=message --report_level=detailed
```

Expect both selected cases to pass. For the recorded sensitivity comparison, a separate source copy changes only the pending case's CpuConfirmationScope from StrictDevice back to AutoFallback, leaving the CpuDiagnostic rejection control and every assertion unchanged. On the recorded CPU-only build that pending case fails the cleanup condition, and the rejection control still passes. This is a fixture-policy before/after, not a production-code revert or a universal GPU baseline claim.

The recorded run compiled the complete maintained test translation unit against identified existing archives and a fresh unchanged base worker object, using the base test-main object. It did not rebuild or execute the complete test_btx target; unrelated target build issues are outside this handoff. Good following work consumes a previously completed real CPU confirmation, not a fresh GPU replay. REPORT.md states all platform, P2P-admission and resource-pilot limits. Log paths use <workspace>/<home>; raw private originals remain preserved.

Prepared with AI assistance and internal review. External maintainer/native-platform review remains separate.
