# Atlas → SwapNet operation contract check

**No product defect found in the reviewed source and twelve unique JavaScript integration checks.** Target release-0.34.17 cd3078e76398b20b7f500acd1348a5b5455f3d5e, macOS26.5.1 ARM64, Node24.13.0. No product fix/build/native app/RPC/wallet/spending or publication.

## Supported path traced

1. SwapNet page's14review-action buttons open operationDialog, without passing an automatically selected swap. This UI currently has no list-row-to-action automatic selection to qualify; existing IDs are entered in the JSON form. Do not invent a missing-selection defect.
2. operations.js uses catalogue defaults, exact JSON parsing/encoding and an explicit wallet-context field. All14review actions have risk=write, so none takes the silent-read branch. Thirteen use a JSON request argument; provider publish/withdraw can omit it, becoming[]. exportswaprecovery uses confirmed password fields/request_object and its adopted821qualification is reused.
3. Actual Bridge.prepare forwards method, exact params_json and wallet|null to atlas_prepare. prepare stores the request/epoch/digest/expiry; execute sends only the prepared ID. Request contents cannot be replaced by changing later form fields. Rust consume removes the ID, checks epoch/age/digest, then commands.rs rechecks the connection, confirms the immutable request, rechecks again and only then calls RPC.
4. src/rpc/swapnet.cpp forwards the first request object or default{} to ExecuteRPC. node.cpp preserves authenticated principal/owner/wallet restrictions and maps backend errors to JSON-RPC errors. Host.rpc in embedded.py rejects wallet context differing from the bound native wallet (WALLET_SCOPE). No inference that Atlas can fund from some other selected wallet; it is refused by the backend.
5. Rust transport returns RPC errors as typed RPC_code errors and uncertain delivery as OUTCOME_UNKNOWN/outcome_unknown=true. Bridge.invoke retains these fields in Error. operations.js shows code/message and the explicit no-retry warning for unknown outcomes; it refreshes after success and does not automatically resubmit failures.

Source/manifests cover51files, including actual native request/host/RPC code and existing tests. All14action definitions/grouping/evidence are in action-inventory.json. This source trace is not execution of native Rust or a confirmation window.

## Existing evidence reused

-821 recovery-export field/request-object, cancellation/unknown/success and clearing controls: previous own DOM tests plus Numair's209webtests/template check. No repeated export tests.
- Current six-status page diagnostic11PASS: not rerun. Native generic approval/cancel evidence and byte-identical source boundaries remain scoped to their original versions.
- Existing operation-prefill tests exercise helper expansion, not page/button → real Bridge routing. recovery-export tests use a fakeApp bridge; their ordinary asset-policy case does not invoke the real Bridge. The sole current frontend Bridge test covers export filename plumbing, not SwapNet operation requests.
- Rust rpc_contract.rs covers encoded wallet URL, native RPC framing errors, immutable approval consumption/epoch and secret redaction. operations.rs unit tests cover permission/state/limits. These tests were inspected, not re-executed or counted as new passes.

## New checks executed

Real SwapNet page/button → operationDialog → actual JS Bridge; only the Tauri invocation boundary replaced with controlled responses. Existing upstream DOM stub reused. Six representative shapes: request quote, accept quote, refund with explicit wallet, nested mandate, omitted provider request with blank wallet, and privileged wallet-info{}. Exact long atom strings remain strings, request data retains identity/fees, inherited/explicit/blank context reaches prepare, and the result is shown after successful execute.

Other checks: editing fields/global wallet during pending prepare cannot rewrite its captured request; CANCELLED and CONNECTION_CHANGED remain distinct errors with no simulated submission; simulated node WALLET_SCOPE refusal remains an error; OUTCOME_UNKNOWN warns against retry; a rejected prepare cannot execute and a later healthy prepare uses the new request. Every outcome makes only one execute call and no automatic retry. Source-equivalent other actions are not separately advertised as executed.

**12uniquePASS, zero selected skips**, assembled from9valid first-run passes plus3focused corrected-fixture passes. First run's three failures were JSON object key-order expectations, not request corruption. Product encodeJson correctly canonicalizes keys; final assertions compare decoded content while preserving exact method/context and immutable captured bytes. Nine valid passes were not repeated. First retry mistakenly ran before the fixture edit due a relative-working-directory mistake, reproduced the same three assertion failures, and touched no product code; corrected sequential runner then passed all three. Raw evidence preserved.

This proves frontend/native-interface argument and outcome handling under controlled replies. It does **not** prove real confirmation ordering, native request consumption, node refusal, signing, funding or native wallet scope by execution. In particular, simulated no-submission counts are not observations of a real node or proof of an authorization boundary. Those Rust/backend behaviours remain source/reused evidence.

## Remaining boundary and next step

Both page/status and this frontend operation check are complete. The broader current native Atlas→node journey remains NOT_RUN, not closed by these component results. A useful remaining native check would connect a matching current Atlas artifact to a disposable empty SwapNet node, cancel a prepared dummy-swap refund and confirm no RPC dispatch, then explicitly approve that same harmless nonexistent-ID request and verify the real typed node refusal plus exact context. No funded swap/real wallet is needed. Reuse generic confirmation controls, and do not rebuild or replay settlement simply for a matrix cell.

Next is **artifact/source feasibility admission only** for that exact native boundary: identify a current compatible saved Atlas app and retained node; if none, state the concrete prerequisite/cost before considering a build. Old afd Atlas lacks the new page/allowlist and is not current proof. The request’s bounded trace/test is complete, and no fix or upstream success-only post is indicated.

## Evidence

source-manifest.json; action-inventory.json; qualification-receipt.json; first-attempt-diagnostic.log; focused-recheck.log; two raw execution receipts; source/gui/atlas/tests/swapnet-action-diagnostic.test.mjs. Each execution had30second outer/10second per-case bounds, under0.2s wall time. No service or child process remains. No existing valid status/export/backend settlement check was rerun.

Lesson: validate request *meaning* independently of object-key ordering; retain canonical bytes only for immutability comparisons. Keep status/form/bridge/native execution as separate evidence scopes within the same campaign instead of closing the umbrella after a component pass.
