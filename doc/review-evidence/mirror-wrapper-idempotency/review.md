# Mirror wrapper correction — independent source review

**No blocking correctness issue found in the reviewed source.** This review reads the candidate wrapper, maintained test method, local probe and current helper idempotency implementation. It does not execute tests or establish native platform qualification.

## Request-key behavior

The wrapper creates one 128-bit random token with secrets.token_hex(16) per logical mutating cmd_mirror invocation, before calling _rpc_dev. The mutation uses one parameter variant; it does not generate a new token inside transport/variant handling. Separate default invocations receive separate operation identities. A caller-supplied --idempotency-key is preserved exactly for intended retries; empty/whitespace-only keys are refused before RPC. A supplied key alone cannot accidentally become a mutation or be silently ignored during inspection.

Read-only mirror still calls getmodelmirror with an empty argument list and does not generate/send a mutation key. The helper's mandatory-key, body fingerprint, cached replay, conflict and nonzero-spend checks are untouched. The new code does not broaden generic RPC behavior or change profile/node CLI conversion.

Documentation correctly requires choosing an explicit key on the original command when retryability after an uncertain result matters, and distinguishes the helper's process-lifetime replay cache from durable protection across restart. It does not claim restart-persistent idempotency.

## Maintained regression and evidence boundary

The default wrapper mutation is the discriminating fail-before/pass-after case. The same candidate maintained method can be executed against either baseline or candidate wrapper. It checks saved selectors and a preexisting unrelated selector, zero spend, explicit-key success/replay/conflict, read-only inspection, invalid wrapper keys, and direct missing-key/nonzero-spend refusals. Setting the saved file timestamp to a fixed past value before replay gives a meaningful no-rewrite oracle even when the contents would otherwise be identical. The existing profile test is POSIX-gated, so this timestamp control does not add an unqualified Windows path.

The local probe separately verifies fresh nonempty keys on two invocations, stable explicit-key forwarding and read-only/invalid-option routing. Its _rpc_dev substitute is source-boundary evidence, not real helper validation. The planned native focused-method execution is not a full feature_swarm_profile_overrides.py run or its node-owned profile/guard/restart qualification.

Optional test strengthening: direct negative controls currently accept any helper error. Checking the expected missing-key and nonzero-spend diagnostic text would prevent an unrelated failure from satisfying those two controls. This is not a source correctness blocker; the native result must still inspect the actual errors and same-body replay/conflict outcomes.

No source, test, driver, runtime, CI, branch or publication was changed by this review. Only this report was written.

Final qualification: suggested negative diagnostics were strengthened before dispatch; native42192725966 passes the same final maintained method only with the corrected wrapper. Original helper checks/source and executable hashes preserved.
