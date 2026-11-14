# Scoped Bitcoin history recovery — evidence

Repair on swapnet-v2 d7b9594b: restoring a committed backup after the original Bitcoin output was claimed can fund a second10000sat output. The candidate persists an imported-session marker and resolves original funding through bounded signer/watch wallet history. Exact decoded script/amount and outpoint matching includes spent outputs; ambiguous/incomplete history refuses fresh funding. Existing funding WAL takes precedence, ordinary fresh sessions are unchanged, and recovered funding bytes are not rebroadcast.

## Verdict and execution identities

- Native baseline43586947214 (harness1018a077): original10000sat paid/claimed9900sat, old restore issued another confirmed10000sat with disjoint inputs.
- Native candidate43589965575 (f8e0a051): exact original claimed payment retained,0fresh funding attempts; original ref and secret_exposed survive reopen. Actual Core30.4 Ubuntu wallet/chain with production Python, simulated BTX. The raw result's target field labels upstreambase d7b9594b; actual candidate isf8e0a051. No whole-swap complete claim.
- Same15component cases:12fail3pass before→15pass after. Separate marker-write failure:beforefail→afterpass. Existing183Python tests pass. Supplemental8matching/lifecycle/ambiguity cases fail before/pass after, with4refusal-code assertions tightened.24cases covered across bounded runs, not a single fresh24case suite. Source hashes in standalone-source.json match tested product modules; standalone commit has final test-only additions.
- Independent code/evidence review found no new blocker in valid-window/newly restored BTC scope. This is not independent native platform verification. Review findings and resolution: independent-review.md and review-closeout.json.

Native run links: https://github.com/sunnyriverr/btx/actions/runs/43586947214 and https://github.com/sunnyriverr/btx/actions/runs/43589965575. Artifacts were downloaded/hash-checked; identities in completion-receipt.json and repair-artifact.json. Native harness/run recipe: repair-native.py and run.sh. Executed fork workflow .github/workflows/spent-recovery.yml atf8e0a051 calls bash ci/spent-recovery/run.sh. These scripts are retained here as the executed recipe, not a claim that running them from this docs folder is identical without its expected CI paths/dependencies.

For maintained component tests: PYTHONPATH=contrib/swapnet:contrib/swapnet/tests python -m pytest contrib/swapnet/tests/test_restored_history.py. Published path is the final maintained test placement; earlier logs used the external test_history_repair.py path. Do not confuse reconstructed test invocation with a new full native run.

## Limits / compatibility

- Bitcoin only; actual BTX leg simulated. No nativeCore32.1candidate, full two-node swap, package, mainnet or release qualification.
- Valid-deadline-window repeat-payment prevention. Existing deadline checks may reject aged/matured committed restores BEFORE history lookup; general late/refunded-backup recovery remains unresolved.
-1000historyrows/wallet bound; exceeding it refuses. Snapshot stability checks are not atomic global wallet/reorg coverage.
- Previously imported unmarked directories require reimport into a fresh directory. No guessed legacy detection. Unreferenced restored unspent candidates also require readable history, to avoid masking older spent matches. Existing signed-WAL/reference recovery remains separate.
- Missing/ambiguous/error controls are component tests. Staged marker failure tested; every possible power-loss point was not tested.

Credit repch1c for earlier backup-recovery reports and Numair for existing adoption code. Scoped AI-assisted implementation/testing and separate code review. No consensus/deadline rule was changed.
