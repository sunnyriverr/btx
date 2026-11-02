# Reproduce

Use unchanged contrib/atlas/neuronlab from6d0fbf6ba492b16bdef64ade30d85ea8dffd287a andacbf7efb20b1b82da06affdae2ead08068cf743c under before/ and after/. source-identities.json verifies the trees. Use Python3.11, Torch2.14.1 and separate exact Transformers4.57.6/5.21.1 environments, with versions457.json/versions521.json recording the other packages. The tested run.py shares cached Torch and selects private dependency targets using PYTHONPATH; replace its local interpreter path for your machine, never a production environment.

check_model.py save <fixture> untied|tied creates actual tiny random models/tokenizers and calls unmodified save_pretrained. check <fixture> before|after <result-label> invokes the actual BTX loader and compares successful results with Transformers. mutate creates the three separate negative controls. run.py records commands/timings. Before rerunning save, use a fresh fixture output location; it refuses to overwrite existing fixtures.

All tests set HF_HUB_OFFLINE/TRANSFORMERS_OFFLINE and local_files_only. Model fixtures need no download or GPU. run.py only verifies child execution succeeded; finish.py asserts the actual expected result statuses, regression sensitivity, refusal controls and exact source identities. Keep both pieces when reproducing. The reverse5.21.1→4.57.6tokenizer failure is expected and disclosed, not treated as a pass.

A narrow handoff should report the two requested save-version cases under5.21.1, the same-version4.57.6and tied controls, three strict refusals and actual platform/framework limits. This does not run a desktop window or qualify a release.
