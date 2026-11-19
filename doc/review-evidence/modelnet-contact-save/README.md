# ModelNet contact save and retry evidence

[Linux qualification run 44488023152](https://github.com/sunnyriverr/btx/actions/runs/44488023152) ran the standalone helper on Ubuntu 22.04 x86-64 with OpenSSL 3.5.9. The verified retained baseline matches the affected source at `a97af7b3`. The candidate was built from that pinned source with [the submitted patch](fix.patch). The [qualification receipt](VERIFIED-QUALIFICATION.json) identifies the exact workflow, fixture and binary hashes.

| Case | Before | After |
| --- | --- | --- |
| Temporary catalog write failure | Reports success and retains contact only in memory | Reports the save error and rolls back the tentative contact |
| Same request after storage recovers | Reports success again, without saving | Saves both contacts |
| Clean stop and reopen | Healthy contact remains, new one disappears | Both contacts survive, including the second reopen |
| Duplicate controls | A previously saved contact is accepted even while writes are blocked | Same, with unchanged durable catalog bytes |

The same [RPC fixture](observe.py) and [#495 lifecycle adapter](pr495.py) produced [baseline exit 2](before.json) and [candidate exit 0](after.json). The named CI step **Build only the helper and compare the identical contact test** ran both cases after verifying signed Jammy dependencies. [Full retained records](https://github.com/sunnyriverr/btx/actions/runs/44488023152/artifacts/14512545386) include the runner logs and source and cache checks.

Linux compares catalog bytes on duplicates. The [Mac component receipt](duplicate-no-persist-component.json) separately records zero calls to the stub serializer from the exact compiled `AddPeer` bodies, including while writes were blocked.

The published branch applies the same patch to `c97c9a8d`. The newer source was checked for patch applicability and unchanged affected code. The test did not run on that head. Full node, peer connectivity, other helper platforms and failed-save behavior in other callers are outside this qualification.

Credit to repch1c for the endpoint validation in [#495](https://github.com/btxchain/btx/pull/495), whose lifecycle fixture this test adapts.
