# Native Mac ModelNet first-run: scoped PASS

Target CLI/test source: main `074dac167c26c1e091198f691ed5727817dba88a`. Reused packaged daemon/helper from `949a98e34222cc4cdb5b1d5bd650aa3b7bcbff72`; relevant runtime/CLI source is unchanged on main (the intervening difference is the Linux Python packager). This is a supplemented-source CLI run, not a fresh main build or untouched package-only test.

macOS26.5.1 arm64/M4, system Python3.9.6, scratch regtest node with wallets disabled, separately launched scratch helper,8MiB quota, no transport listener/peer following/LAN discovery/NAT-PMP. Compiled helper reports OpenSSL3.5.9; CLI environment pins Homebrew OpenSSL3.6.3. No remote handshake.

## Observed result

Eight required rows PASS: node/helper readiness, doctor, init, profile show, tiny safetensors structure check, directory host, LOCAL search, owned cleanup. Search returns the exact host model ID/URI. Coverage local=true/global_complete=false. Host is PINNED, metadata signed, no automatic spending. The44-byte/two-file fixture has zero tensors: structure verification is not useful-model admission or inference. Init initialized=true; ordinary setup had already created its non-wallet publisher identity, so identity_created=false.

Both children exit0; socket disappears, recorded PIDs absent and ports bindable. No production wallet/node/cache used. Restart persistence, single-file hosting, full feature_modelnet_btx_model.py, inference, peers/transfers, cloud recovery and other platforms were not tested. No release qualification.

## Setup correction

First attempt incorrectly passed helper-only `-modelnatpmp=0` to btxd. Daemon rejected it before workflow execution; both test children exited. Removed only that node argument after checking the retained daemon's help; the separately launched helper still receives NAT-PMP disabled. Fresh run passes all rows. This is a harness correction, not a product fix; both receipts are retained. One earlier remote freshness request was malformed; the correctly formed prepublication API read confirms main074.

## Inputs and reproduction

Archive SHA256 `22ee49b866f7d1539387d7e30bc82b38174b0925e84a103f590d92485569de73`,46,410,625bytes. Immutable artifact14148375421 from [run43679857514](https://github.com/sunnyriverr/btx/actions/runs/43679857514), expires29Nov2026. [Prior archive provenance](https://github.com/sunnyriverr/btx/blob/e7e1954fa9b7ebe24eff01586ad2adca8693248f/doc/review-evidence/integrated-mac-949/README.md) is reused; no repeat archive/signature suite.

`packed-identities.json` records wrapper/native hashes. Exact CLI source is [contrib/modelnet/btx-model](https://github.com/btxchain/btx/blob/074dac167c26c1e091198f691ed5727817dba88a/contrib/modelnet/btx-model). `first_run.py` is the executed harness;13 offline controls passed. In manifest-template.json, replace `<EVIDENCE_ROOT>` with the restored local evidence directory containing package/btx-0.34.16 and the exact CLI saved as btx-model-source.py; keep expected hashes unchanged. This path-adjusted public reconstruction has not itself been rerun:

```
python3 first_run.py --self-test
python3 first_run.py --run --manifest manifest-template.json --scratch /tmp/btx-s2-first-run-074-UNIQUE --rpc-port 39621 --p2p-port 39622 --deadline 900
```

Use fresh owned paths and free ports, preserve1.25GiB disk reserve. Required skipped/malformed/error/timeout outcomes cannot pass. Native execution used the exact local manifest before path redaction. Paths are redacted; raw response values and outcomes are preserved. `final-result.json`, `setup-attempt.json`, node/helper logs and `execution-receipt.json` are the entry points. No cookies, private keys or wallets included.

Credit: JPP's existing first-run fixture/setup/assertions; Numair's integration; retained archive produced by Sunny's separate package lane. This run deliberately covers a bounded positive subset, not all optional fixture calls.
