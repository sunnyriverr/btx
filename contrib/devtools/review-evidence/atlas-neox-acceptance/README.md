# Atlas273 item5: actual GPT-NeoX checkpoint reload

Scoped acceptance for Numair's acbf7efb fix; original failing matrix by Jpp-matata. Candidate code is Numair's, unchanged. Independent Mac CPU experiment by Sunny River, AI-assisted. This commit adds evidence only to acbf7efb; no product change or new PR.

Start with REPORT.md and the JSON before/after results. Actual Transformers5.21.1 loading unmodified untied save_pretrained checkpoints from4.57.6and5.21.1 gives WEIGHTS on6d0fbf6b and passes onacbf7efb. Successful loads match the same environment's Transformers reference tensors and logits. Controls remain strict. One execution per case/source, not3repeat runs. Actual Python3.11.14/Torch2.14.1/CPU; JPP used Linux/Torch2.10.0. No GPU/UI/mainnet/full-suite/release qualification.

The reverse5.21.1save→4.57.6load fails at AutoTokenizer TokenizersBackend on both revisions; it is disclosed, not presented as a passing compatibility test.

## Reproduce without model downloads

Use a disposable Python3.11 environment with torch==2.14.1. Install the exact other dependency versions from versions457.json/versions521.json into separate deps457/ and deps521/ directories beside these scripts. For example, install transformers==4.57.6 and transformers==5.21.1 respectively, with the recorded tokenizers/numpy/hub versions. Avoid modifying a production Python environment. Keep1.25GiBfree.

Fetch the two source commits and extract their unchanged contrib/atlas/neuronlab directories into before/ and after/. source-identities.json records every file hash. From the BTX checkout, with this evidence directory set as EVIDENCE_DIR:

    mkdir -p "$EVIDENCE_DIR/before" "$EVIDENCE_DIR/after"
    git archive 6d0fbf6ba492b16bdef64ade30d85ea8dffd287a contrib/atlas/neuronlab | tar -x -C "$EVIDENCE_DIR/before"
    git archive acbf7efb20b1b82da06affdae2ead08068cf743c contrib/atlas/neuronlab | tar -x -C "$EVIDENCE_DIR/after"

Inside the evidence directory, set NEOX_TEST_PYTHON to that disposable interpreter, then run:

    python3 run.py
    python3 verify_results.py

check_model.py is the exact executed harness. run.py differs from run.executed.py only by selecting the interpreter through NEOX_TEST_PYTHON/sys.executable instead of a sanitized local cache path (plus importing sys). verify_results.py contains the measured audit's final result assertions, without local source-checkout bookkeeping. Both entry-point adaptations are packaging changes, not newly rerun runtime evidence. Exact executed run/finish copies and command timings are retained. Run only in a fresh copy: save refuses to overwrite existing fixture directories.

run.py checks child execution; verify_results.py checks expected semantic PASS/REFUSED/ERROR outcomes, so both are necessary. It intentionally expects the reverse-tokenizer boundary to fail. No tokenizer file is edited to mask it. Locally generated fixtures are small SafeTensors, recreated by the script; fixture-save records retain their hashes. No model/config/tokenizer downloaded. No cache, framework binaries or model credentials are published.

Publication update: JPP subsequently posted broader item5 confirmation at https://github.com/btxchain/btx/pull/273#issuecomment-6573352127. This handoff is independent confirmation under Torch2.14.1, not a claim the gap remains untested. The reverse-version tokenizer limitation is specific to our locally generated generic tokenizer save.
