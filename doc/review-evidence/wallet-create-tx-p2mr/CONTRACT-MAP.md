# Five transaction-creation checks mapped to P2MR

Source-only mapping at release1e2f8b5f12295002334d3390c12cac0bb4ae2aff. No product/test code changed, imported, compiled or run. Source snapshots were read/downloaded only. JPP's observed unsupported-address stop and our #774 native receipts remain separately attributed evidence; no claim this whole script has passed.

## Shared setup and existing evidence

The registered script has five methods, in order: anti-fee-sniping locktime, fee-cap refusal, too-long mempool chain, default version, and setfeerate. JPP774 says his execution stopped on the bech32 request in the second method. Later methods therefore need a source/contract check, not an assumption that they already ran successfully.

The existing200-block mature setup yields ample funds under20BTX subsidy:25BTX funding requests need multiple mature coins but are not inherently invalid. Do not mechanically divide all existing amounts by Bitcoin/BTX subsidy ratio. An isolated fixture using only one mature coin must use different funding arithmetic. Preserve the inherited old-tip/recent-tip sequence for locktime assertions.

Native #774 receipts prove a100-ancestor P2MR chain of387300vbytes can be constructed on the exact1e2CPU profile, with each self-spend3873vbytes at2sat/vB in that run. They prove that one selected signing path, not every PQ leaf. Reuse the CPU/funding/chain recipe and source-size observations; no need to rerun the completed duplicate-group payment case.

TestNode.start (saved current source:254-268) substitutes self.extra_args only when no explicit args are supplied. restart_node(extra_args=[fee_setting]) therefore must preserve intended CPU/node isolation settings explicitly in a later adaptation. TestNode already appends economic/cpu-diagnostic regtest settings if absent; do not claim those defaults are wholly lost. Other activation/isolation/autoshield/fee settings still need deliberate preservation, without carrying a previous row's fee override into the next.

## 1. test_anti_fee_sniping — preserve the behavioral assertions

**Supported contract:** sendtoaddress, send and sendall select locktime0 against an old tip, then a positive height-based locktime no greater than the current tip after a recent block. P2MR does not remove this transaction-level behavior. For sendall, add_to_wallet=false must still return a completed signed transaction without emptying the wallet.

**Source:** wallet/spend.cpp:1171-1226 checks initial-download state and an8hour tip-age threshold, then chooses current height with occasional backward randomization. At height201 a randomized subtraction below100still leaves a positive value. CreateTransaction uses DiscourageFeeSniping around1512-1518 unless caller supplied a locktime. rpc/spend.cpp:292 calls MaybeDiscourageFeeSniping2 from FinishTransaction, including send/sendall. No explicit timelock argument should bypass this path.

**Mapping:** use supported P2MR addresses; retain old-block mocktime, clear mocktime, then mine the recent block and assert the node is current/not initial block download. Preserve exact0 and0<locktime<=tip oracles across all three callers. Avoid reordering this method after fee-setting/restarts that change prerequisites. No new error acceptance or method skip.

**Evidence/limit:** source-supported, JPP's stop is later in the script but is not our own per-method PASS receipt. No new execution.

## 2. test_tx_size_too_large — P2MR-compatible setup for the same maximum-fee refusal

**Supported contract:** despite the method name, its actual oracle is the wallet maximum total fee, not the standard maximum transaction size. sendmany must return RPC-6 and fundrawtransaction RPC-4 with the specific maximum-fee message when the requested/selected fee exceeds that cap. Cover the three startup fee sources, settxfee and setfeerate without falling into dust/unsupported-address/insufficient-funds setup errors.

**Source:** addresses.cpp:125-154 accepts only p2mr. policy.cpp:51-98 computes dust; BTX scale1 adds148bytes to serialized output size, rather than a discounted PQ witness estimate. A34byte P2MR script yields43byte serialized output; at default dust-relay3000sat/kvB threshold is573sat. The current2500sat output is therefore above ordinary default dust: **do not raise its amount merely because the real PQ signature is large.** policy.h gives fixed dust default/dustdynamic off; if a later profile enables dynamic dust, establish its actual threshold instead of assuming this calculation applies.

wallet.h:152 has DEFAULT_TRANSACTION_MAXFEE=COIN/10 (0.1BTX).400P2MR outputs alone serialize to17200bytes, before input/header/change;0.01BTX/kvB or1000sat/vB already implies output-only fee0.172BTX. Thus the same maximum-fee condition is plausible without exceeding MAX_STANDARD_TX_WEIGHT1.2M. wallet/spend.cpp:1637-1638 refuses current_fee above wallet cap; RPC SendMoney maps construction failure to-6, RPC FundTransaction to-4.

**Mapping:** replace unsupported bech32 setup with P2MR; retain400outputs/valid amounts if default dust and funding checks hold. Keep exact expected codes/messages and all fee-source rows. Preserve startup profile across restarts, reset per-wallet fee overrides, and establish sufficient funds/valid output script values. A future run must reach the specific fee-cap error, not an earlier error. No limit relaxation or all-errors-allowed list.

**Evidence/limit:** author observed unsupported address; source arithmetic supports adaptation. Actual high-fee path under the full P2MR fixture remains unexecuted.

## 3. test_create_too_long_mempool_chain — replace inherited setup assumptions, preserve refusal

**Supported contract:** with walletrejectlongchains enabled, an otherwise affordable send using only a long unconfirmed chain must be refused with the specific long-chain error. This differs from774: there must be NO independent confirmed coin that could fund the final request.

**Source:** policy.h defaults100ancestors/descendants and1024kVB. wallet/spend.cpp:1059-1064 reads those limits; filters around1094-1118 top out atmax-1 under normal rejection. At1136-1141 the long-chain diagnostic is selected when the discarded long-chain value could cover the request. RPC send/FundTransaction uses-4 for its construction failure; keep that existing API-specific code.

**Incompatible inherited setup:** it builds only25transactions. Increasing that loop to100alone is wrong:25-i recipient amounts become zero/negative after25. It also assumes recipient vout1/change position0 while accumulating change outputs. These are fixture mechanics, not required product behavior.

**Mapping proposal:** reuse774's supported single-output self-send recipe, starting from a confirmed1BTX coin in a dedicated wallet, then100normal self-spends to fresh P2MR addresses. Verify exact ancestor count, serialized chain size, single remaining spendable tip and lack of alternative eligible coins.1BTX leaves ample headroom for0.3plusfees (unlike774's0.3initial coin, whose final value0.292252cannot cover0.3). Then invoke the original send API with minconf0/include_unsafe/add_inputs and expect its exact-4long-chain refusal. No extra independent0.7coin and no duplicate774final success case. Confirm required options/path in a later source draft; no new claim that this shape has already run.

**Evidence/limit:**100chain recipe executed in774; this exact final send/refusal with1BTX funding has not. Do not call the inherited25case a reproduced product failure.

## 4. test_version3 — preserve version2

**Supported contract:** ordinary wallet-created transactions default to version2. Availability of version3/TRUC elsewhere does not change this expectation.

**Source:** primitives/transaction.h:318 defines CURRENT_VERSION2. This path creates a normal send without timelock leaf adjustments or explicit version override. P2MR signatures do not themselves require changing transaction version.

**Mapping:** retain exact version2 assertion and P2MR destinations. Keep sufficient mature funding, decode through owning wallet gettransaction (works without txindex), and unload the disposable wallet. The inherited25BTX payment is affordable with the existing200-block mature wallet; reduction is optional simplification, not a mandatory protocol fix.

**Evidence/limit:** source-supported; no separate native version test run by this task. Do not change expected version to match a surprising runtime result without reviewing the contract.

## 5. test_setfeerate — preserve rounding, refusal and prior-state checks

**Supported contract:** fee rates accept three-decimal sat/vB precision, reject below-relay/below-wallet-minimum/above-maximum settings while keeping previous value, handle invalid fixed-point forms, and clear the setting on zero. This API does not depend on address type.

**Source:** rpc/spend.cpp:642-714 constructs CFeeRate from AmountFromValue andCOIN, compares relay/wallet minimum and maximum, updates only accepted/zero state, and returns prior fee_rate plus structured result/error. wallet.h sets default minimum1000sat/kvB and max total fee0.1BTX; the RPC's max-rate conversion yields10000sat/vB. feerate.cpp:54 formats SAT_VB with three decimals; feerate.h:17-18 defines CURRENCY_UNIT BTX and CURRENCY_ATOM **sat**. Current sat/vB messages are valid BTX API output, not a reason for cosmetic replacement.

**Mapping:** retain amounts, rounding values, exact messages and paytxfee assertions, including rejection while already set and unset. Preserve node base profile on the restart adding mintxfee0.00003141/incrementalrelayfee0.00001. At3.141sat/vB, reported paytxfee0.00003141BTX/kvB is consistent. Do not conflate returning an error field with throwing an RPC exception; existing test distinguishes those cases correctly.

**Evidence/limit:** source-supported, no newly observed drift or need to weaken this method. Runtime remains unexecuted within this task.

## Verdict and next step

All five contracts are meaningful for P2MR. Clear adaptations are the unsupported output-address setup, the too-short/fixed-amount chain recipe and preservation of deliberate restart profile. Locktime/version/fee-state oracles should remain intact; default dust and sat/vB assumptions must not be replaced with guesses based on PQ sizes or branding.

The next useful action is a narrowly scoped **test-only draft** of the existing script using this map, followed by source review. Before editing, recheck source/owner/author work and claim test/functional/wallet_create_tx.py. No native execution, new build, public workflow, product fix or post follows automatically from this mapping. Previous774 result is evidence reuse only. Both peers remain separate, and personal wallets untouched.
