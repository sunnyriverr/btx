# Focused model-search conversion review

Reviewed exact accepted base `666673a3153225ba264c7870e0e82e354df86765`, the three-row candidate in `src/rpc/client.cpp`, and the new maintained `rpc_convert_values_model_search_text_or_object` case in `src/test/rpc_tests.cpp`. Read-only source review; no build, execution, network request, helper/wallet operation or product/test edit performed by this reviewer.

## Verdict

No correctness blocker found in the narrow text-or-object repair. Scope is exactly `searchmodels`, `searchpublishers` and `searchcollections`. The existing `json_object` mechanism is preferable to only `also_string=true`: `ConvertArg` at client.cpp817-832 parses an object and otherwise preserves the raw string. `also_string` would still convert JSON-looking search text such as `70`, `true` and `null` to non-string values.

The handler contract supports that choice: modelnet.cpp419-423 documents searchmodels as query object or text; helper.cpp7364-7376 passes it to ParseSearchQuery, whose search.cpp590-600 explicitly accepts STR and OBJ and rejects other types. helper.cpp7825-7826 accepts publisher query objects or text; helper.cpp7855-7857 accepts collection text or object.text. These sources support preserving non-object CLI argument text rather than sending numbers/booleans/arrays as typed search queries. No inference is made about object-only browse/feed methods; they are unchanged.

The regression keeps both positional and named forms, raw text identity (including JSON-looking scalars, arrays, quoted text, malformed-object text and equals signs), empty/omitted input and two object controls. Object payload identity is compared after conversion. Existing tests/assertions are unchanged. Null-initialized result checks avoid cascading dereference failures after an expected baseline exception; they do not excuse the failed conversion.

## Material limits / compatibility note

- Previously, a JSON-encoded string argument such as the literal bytes `"llama"` was decoded to `llama`; the new rule treats those bytes as literal search text including quotes. That is consistent with the explicit raw-text-or-object contract and is deliberately asserted by the new test, but a handoff should mention it if the old JSON-quoting workaround was user-visible. This reviewer finds no documented promise that JSON string unwrapping must be retained for these CLI inputs.
- Standalone execution of the exact maintained case body with the real converter qualifies the component behavior. It does not qualify the full `rpc_tests` fixture, full `test_btx`, actual helper search results, RPC transport or a full node build. Keep that distinction in evidence.
- Object controls prove type/payload preservation; they do not claim handler validation was executed. Invalid object field handling remains the unchanged helper's responsibility.

A mutant using `also_string=true` would fail the numeric/bool/null/array/string-identity checks; removing conversion entirely would fail the object controls. Thus the case challenges both tempting incomplete repairs.
