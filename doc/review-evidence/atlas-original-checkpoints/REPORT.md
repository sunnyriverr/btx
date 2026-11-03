# Original Pythia full-loader acceptance

**PASS on afd65919: full load_local accepts original pythia-70m and pythia-160m with their original tokenizer files under Transformers5.21.1.** Both produce usable model, tokenizer, adapter and binding; learned tensors and short-input logits match ordinary Transformers loading exactly (maximum difference0.0).

## Why this run

Fresh coverage review found repchic had just covered both original models using the strict weight helper in Transformers4.57.6, with older-loader failures. His comment explicitly omitted full load_local/tokenizer and Transformers5: https://github.com/btxchain/btx/pull/273#issuecomment-6604161908 . The task narrowed to that missing supported entry point. The earlier helper-only baseline and broad matrix were not rerun. Numair's request: https://github.com/btxchain/btx/pull/273#issuecomment-6602199759 . Native Windows/ACL and loaded-wallet UI evidence was also added by repchic6603952009 and is recorded in coverage.json; do not duplicate it.

## Exact scope and observation

Source afd6591970e7f8d65871412b9d7cf03b48f30b97 exported from immutable Git objects; models.py SHA256c97a93395cc12d093c6e34c70e06515e160655f4454a8ec2141dbc6e8885db29 verified. Entire exported manifest in source-manifest.json. macOS26.5.1/M4 arm64, Python3.11.14, Torch2.14.1, Transformers5.21.1, SafeTensors0.8.0; complete versions in each result. These satisfy declared package ranges but differ from authoring/tested pins. Existing dependencies reused read-only; no package installation.

Published files were acquired at pinned publisher revisions. Full model hashes verified, and actual headers contain18legacy buffers among94tensors (70m),36among184(160m). checkpoints.json contains revisions, hashes, URLs and buffer names. Original files were not re-saved or modified. Only model.safetensors and necessary tokenizer/config JSON downloaded, approximately545MB total; no pickle weights or remote code. Runtime uses local_files_only, trust_remote_code=False and offline environment flags.

Each model ran once, sequentially, CPU with one Torch thread. load_local returned all four documented objects. Its tokenizer encoded a fixed prompt, clipped to12tokens; token IDs matched independently loaded AutoTokenizer. All live model tensors matched a separate AutoModelForCausalLM loading of the same original directory. Both full12token logit arrays were finite and exactly equal. Adapter output-head access and shape matched the model head; interventions, hook sites and adapter calculations were not exercised. File hashes before/after match.70m:3.09seconds within case, peakRSS1.139GB.160m:3.16seconds, peakRSS1.560GB. Case timings exclude acquisition/process startup; no performance benchmark claimed.

## Limits and handoff

This is local model-loading acceptance, not native Neuron Lab UI, signed profile/Service admission, GPU, Windows/Linux, sharded checkpoints, full suite or release qualification. A changed execution fingerprint still requires profile review and signing; these results do not authorize an old signed profile. No source fix was needed. Existing unrelated-key refusal evidence and maintainer tests are reused; no new refusal matrix here.

## Evidence and execution

See README.md for the recorded entry point and source setup. check_load.py and acquire.py are byte-identical to the executed originals. Both successful cases are recorded in runs.json and the per-model JSON/log files. Internal review is in review/REPORT.md. No new runtime was launched to publish this evidence.

Execution and internal review used Codex. Repchic's earlier strict-helper and old-source results are his independent executions, reused and attributed above.
