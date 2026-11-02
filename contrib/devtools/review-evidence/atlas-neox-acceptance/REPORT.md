# Atlas #273 item5 — actual GPT-NeoX acceptance, private

**Requested failure reproduced on6d0fbf6b and corrected onacbf7efb: Transformers5.21.1 loads untied checkpoints saved with actual4.57.6 and5.21.1.** No product changes or public post.

Demand: Numair's item5 at https://github.com/btxchain/btx/pull/273#issuecomment-6570878019. JPP's original actual-model matrix: https://github.com/btxchain/btx/pull/273#issuecomment-6496955030. Fresh targeted PR/comment/search read found unchanged acbf7efb and no published after-result. This executes only the narrow acceptance gap, not JPP's architecture matrix.

## What executed

macOS26.5.1/AppleM4, Python3.11.14, CPU with one Torch thread. Cached torch2.14.1 reused read-only; JPP's earlier Linux matrix used2.10.0, so this is independent evidence under a different supported Torch version, not an exact reproduction of his full environment. Transformers4.57.6 and5.21.1 installed into separate private target directories with their resolved dependencies. Exact versions: versions457.json/versions521.json. No GPU, running Atlas UI, node, wallet or model download.

Each real GPTNeoXForCausalLM has one layer,32hidden units,4attention heads,64intermediate units,32-token vocabulary. A deterministic local WordLevel tokenizer accompanies the fixture. The actual libraries' unmodified save_pretrained methods write SafeTensors/config/tokenizer files. All check runs are offline/local-files-only with remote model code disabled. Fixtures and file hashes are retained; negative fixtures are separately mutated copies, not relabelled pristine saves.

Same check_model.py tests full btx_neuronlab.models.load_local(root,device='cpu') against both unchanged repository revisions. Every successful load checks all model state tensors and a fixed-input logits result against Transformers' own from_pretrained loader in that same environment. Tensor equality holds and maximum logit delta is0. This checks the small fixture's reload fidelity, not all architecture behavior or cross-device numerical equivalence.

|Saving Transformers|Loading Transformers|Old6d0fbf6b|Newacbf7efb|
|---|---|---|---|
|4.57.6, untied|5.21.1|WEIGHTS: missing lm_head.weight / unexpected embed_out.weight|PASS, weights/logits match|
|5.21.1, untied|5.21.1|Same WEIGHTS refusal|PASS, weights/logits match|
|4.57.6, untied|4.57.6|PASS|PASS|
|5.21.1, tied|5.21.1|PASS, tied storage|PASS, tied storage|

One final execution per case and source revision. This is2/2 distinct requested scenarios, not3repetitions. In5.21.1, three malformed copies (unrelated extra tensor, second missing tensor, missing untied head) still give WEIGHTS on both source revisions:3/3negative cases per revision. These exercise the one-mismatch restriction without a product patch or fabricated framework class.

## Additional boundary, kept explicit

The extra reverse-direction probe—5.21.1 checkpoint/tokenizer loaded by4.57.6—fails on both code revisions at AutoTokenizer: `Tokenizer class TokenizersBackend does not exist or is not currently imported`. The changed strict-weight code is not reached. This does not contradict the requested5.21.1acceptance result, but it prevents claiming unrestricted bidirectional saved-directory compatibility. No tokenizer file was edited to disguise this failure and no unrelated compatibility fix was attempted.

## Integrity, scope and disposition

Source before:6d0fbf6ba492b16bdef64ade30d85ea8dffd287a. After:acbf7efb20b1b82da06affdae2ead08068cf743c. Every extracted file is byte-checked against its Git object in source-identities.json. Corrected models.py SHA256 matches Numair's code-manifest value dcfe819ce80c1f9aef299c54020a6f91265dea3b5f0ef0dbfe050d4ca1b4de93. Result records separately retain source SHA384. An initial finish-script assertion compared the quoted SHA256 with SHA384; corrected the audit algorithm and reverified Git bytes, with no source/runtime change or repeated test.

No Linux/Windows, MPS/CUDA, full Neuron Lab suite, production checkpoint, signed-profile requalification, actual desktop workflow or release qualification. Execution-fingerprint values are recorded; old signed profile admission was not exercised. AI-assisted experiment. No independent reviewer result implied.

Fresh dependencies occupy about225MiB combined. Existing Torch environment and repository checkouts were not modified; standalone child processes have exited. Synthetic fixtures/evidence/private dependency targets retained for reproduction. More than2GiB remains free. No production/wallet/miner changes, new PR, push or public comment.

**Next:** one short item5 Tested ACK at the exact Atlas head with this evidence on a proper branch when publication is authorized. No new product fix, repeated25-model matrix or additional generic tests needed for this scoped result.
