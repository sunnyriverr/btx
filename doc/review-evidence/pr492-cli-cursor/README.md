# PR #492 scoped CLI conversion and event cursor evidence

The documented cursor object and `btx-model events --cursor 42` both return events 43 and 44. The bare numeric CLI token is forwarded as the JSON string `"42"` by both converter revisions and returns events 41 through 44, the same page as an omitted cursor. Sending the JSON number `42` directly also returns 43 and 44. The tested difference predates #492.

| Scope | Identity and result |
| --- | --- |
| Native converter | macOS. Stock `dac9aee53520bd49ed320ec7a49b9072fc7d88d9` and #492 `293be9ef3db97dc8cb6be8c503062b4ddf0b5f5c`, with exact client blob `99e6883766980ec36c757efea0dfe571a3a288d7`. 32 checked results include unchanged plain watch IDs, structured queries, the named `listdepositutxos minconf` conversion and two hypothetical watch-row variants. |
| Event fixture | Private temporary journal with sequence numbers 41, 42, 43, and 44. Eight checks used the same journal and actual helper Unix RPC. The journal bytes were unchanged and the helper exited cleanly. |
| Helper | Retained native macOS helper from `cbf65894e6d61084527cd93e913a00c6794418dd`. The two event/journal source files and their headers match `dac9aee5` byte for byte. The relevant helper forwarding block matches separately. |
| Operator wrapper | Exact `contrib/modelnet/btx-model` from `dac9aee5`, executed with `--socket <fixture socket> --json events --cursor 42`. Returned 43 and 44 with next cursor 44. |
| Limits | The tested boundary combines the native converter output and actual helper Unix RPC. Daemon HTTP relay, a complete current-source helper build and the full `rpc_help.py` test were outside the run. |

The [release documentation](https://github.com/btxchain/btx/blob/dac9aee53520bd49ed320ec7a49b9072fc7d88d9/doc/modelnet/events.md) shows the wrapper and cursor object. The [wrapper](https://github.com/btxchain/btx/blob/dac9aee53520bd49ed320ec7a49b9072fc7d88d9/contrib/modelnet/btx-model#L2301) also has a direct numeric JSON fallback. No documented bare numeric `btx-cli` example was found in the checked release tree.

[Event sequences and exact hashes](event-cursor-results.json) · [Converter results and build commands](converter-results.json) · [Converter probe](probe.cpp). Build command paths rooted in the test workspace are shown as `<workspace>`.
