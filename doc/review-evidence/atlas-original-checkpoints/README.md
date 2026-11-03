# Atlas original Pythia full-loader acceptance

Read REPORT.md and summary.json first. Exact Atlas source: afd6591970e7f8d65871412b9d7cf03b48f30b97. This fills the full load_local/original-tokenizer/Transformers5 gap explicitly omitted by [repchic's complementary check](https://github.com/btxchain/btx/pull/273#issuecomment-6604161908).

## Recorded environment

Native macOS26.5.1 arm64/M4; Python3.11.14; torch2.14.1, transformers5.21.1, safetensors0.8.0, tokenizers0.23.3, numpy2.4.6, huggingface-hub2.4.0. These satisfy declared package ranges but differ from requirements-tested.txt. Dependencies were reused from isolated caches without installation or changes. No exact authoring-pin or GPU qualification is claimed.

## Entry point and source setup

Use Python3.11+ with the recorded dependencies. From this evidence directory, export the exact repository source into source/ (BTX_REPO points to a local BTX clone containing that commit):

```sh
mkdir -p source
git -C "$BTX_REPO" archive afd6591970e7f8d65871412b9d7cf03b48f30b97 contrib/atlas/neuronlab | tar -x -C source
python3 acquire.py
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 check_load.py pythia-70m
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 check_load.py pythia-160m
```

The recorded execution used an additional empty HF_HOME and isolated PYTHONPATH for its cached dependencies; use equivalent isolation for reproduction. The executed entry point is check_load.py, invoked once per model in sequential subprocesses with a240-second parent timeout. It propagates any assertion/exception as nonzero and always writes its case result. Inspect both status fields; both must be PASS. No extra portable wrapper was executed or is supplied.

acquire.py downloads only pinned public SafeTensors/config/tokenizer files (about545MB), validates full weight hashes, inspects legacy buffers and preserves a1.25GiB free-space floor. Checkpoints are absent from this Git branch. The acquisition and runtime are distinct: runtime uses local-only framework loading and disables remote model code. source-manifest.json pins all42 exported source files; checkpoints.json pins publisher revisions, downloaded bytes and actual buffer names. Output files contain no credentials or production wallet data.

## Limits

Reference is ordinary Transformers reading the same original files, not a separate mathematical implementation. Adapter check covers returned object/output-head access and shape, not intervention/hooks. Two single-file models and one12-token input each; no new same-environment before control, UI, signed-profile admission, GPU, sharded files, full suite or release qualification. Repchic supplied the older-loader refusal and4.57.6 helper results; this run did not repeat his matrix.

SHA256SUMS.json verifies the sanitized package. The two scripts are identical to their executed bytes. No model files, dependencies or product changes are included.
