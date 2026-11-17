# Native controller source review

Scope: read-only `native_pair.py`, production `application.py`, `coordinator.py`, `journal.py`, `drivers.py`, `evm_driver.py`, `evm.py`, and existing `SwapNetHTLC.sol`. No controller/module execution, network test, build, or publication. Parent controller is not edited. Reviewed initial controller version; line numbers below describe that version.

## Blockers before execution

1. **ETH funding allowance is zero.** `cap(eid)` and `recovery_cap(eid)` both return `2*10**15` (lines 320–321). `EVMDriver.prepare_funding` computes funding allowance = local cap − refund reserve and requires it positive. Both N1 maker ETH funding and N2 taker ETH funding fail `FEE_CAP`. Give funding a separate positive allowance within the existing finite mandate.

2. **N2 can mine the short funding before stopping the taker.** The unconditional mempool mining block at lines 351–352 runs for refund too. Maker broadcast can occur after the view/operation snapshot and before the mempool query. That mines twenty confirmations before the next loop checks funding and stops the taker. Restrict this observation-loop BTX mining to N1; N2 only needs EVM mining until the native short funding is observed. Preserve the zero-confirmation and secret-not-exposed checks.

3. **N2 maturity bound rejects the normal product deadline.** Line 252 allows at most 300 blocks. Production short deadline is `ceil(21600 / fastest_block_seconds)`; BTX target 90 gives fastest 45, hence 480 blocks. With no short-funding confirmations mined, ~480 remain. Increase the fixture's finite admission bound to cover the actual planned deadline; do not shorten product terms.

## Receipt gaps that can admit a false PASS

- `check_leg` only asserts positive confirmations for native funding and claim (line 201); assert the actual supported BTX depth of 20 for both, independently of product `complete` state.
- `native_refund` proves the balance delta and individual refund cap, but does not assert original funding fee + refund fee <= local fee authorization (500000 atoms). Add that cumulative assertion and preserve the individual agreement refund cap. It currently only requires funding fee >0.
- `verify_evm_leg` independently bounds settlement+withdrawal by the agreement claim/refund cap. Its interface has no outgoing local funding cap; the controller must additionally compare its returned funding fee plus the relevant recovery reserve/fees to the local authorized cap when claiming cumulative outgoing exposure. Compare fees within the same asset and same account; do not add opposite-leg fees denominated in another asset.

## Source checks passed, with execution limits

- Native calls enter retained daemon public RPCs; no fake Host/Coordinator or simulated BTX is constructed. `getswapnetworkinfo.in_process`, original outpoint checks, persisted operation `state`, public safe-view `agreement/refs/secret_exposed`, `foreign_accounts[].address`, `listswapoperations.operations`, and parameter dictionaries match inspected production source.
- ETH helper matches `getSwap` seven-word layout, sender-scoped ID, `lockNative(bytes32,bytes32,address,uint64)`, `claim(bytes32,bytes32)`, `refund(bytes32)`, `withdrawAmount(address,address,uint256)`, and exact indexed/nonindexed event layouts. Claim witness is checked in memory but never returned. Gas accounting uses wei = gasUsed × effectiveGasPrice. Helper checks the contract commitment and historical/finalized runtime identity in addition to parent's approved runtime pin.
- Python orchestration uses portable standard-library APIs; no Linux-only timeout/readlink/proc requirement appears in this file. Binary/environment/Anvil startup and the exact deployed artifact remain the parent launcher's responsibility. Source review does not establish Mac runtime behavior or Anvil finalized-tag behavior.

## Final narrow pre-dispatch check

No remaining concrete blocker found in the reviewed launcher and corrected controller sections. Earlier ETH allowance, N2 pre-stop mining race, deadline-bound, depth and cumulative-fee findings are corrected. Source AST parsing passed; no modules were imported or executed.

The launcher retains exact source/build/dependency identities, restores the existing BTX build without rebuilding it, bounds each controller process group, confines datadirs to owned scratch, and shuts down owned Anvil processes. Contract-only compilation is explicit. This is source admission, not a runtime result.

Reviewed file SHA-256 values:

- `run.py`: `675ffedf1038438942530dc356daa54582b8a15a0bbb848ac85bccf78af494d6`
- `native_pair.py`: `5edc08b45c3d8bd3b4c60da1710017dd78a7a97adcdc10e80426f06bb1d38505`
- `evm_verify.py`: `eab2f85d4b8c5371d233b130c48b671cc77ce1e8de7aaa9711ed7c6d5969180e`

Parent platform-input check after review: removed -modelnet=0 because the retained ModelNetOFF build does not register that option (reused Session3 native wallet fixture records this at lines41–43). Native start flags otherwise retain documented CPU wallet test profile. Cleaned stale inherited wallet-fixture manifest fields; exact14315282277/build44053621896 identities remain. AST rechecked; no runtime claim.
