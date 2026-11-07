"""Compare selected source-backed contracts with native declarations and conversions.

This consumes test records, not RPC requests. It is deliberately not a complete
RPC schema or handler-acceptance oracle. Every finding remains a failing result.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import re

from comparison import Finding, Probe, compare, metadata_findings, record_error

TYPES = {'OBJ', 'ARR', 'STR', 'NUM', 'BOOL', 'OBJ_NAMED_PARAMS',
         'OBJ_USER_KEYS', 'AMOUNT', 'STR_HEX', 'RANGE'}
STATUSES = {'AVAILABLE', 'MISSING', 'ROUTING_MISMATCH', 'FACTORY_ERROR'}
# These two selected contracts have independent source anchors. skip_type_check
# alone never permits a union or establishes a handler's accepted inputs.
SOURCE_UNIONS = {('getmodel', 'params[1]'): 'json_or_string',
                 ('searchmodels', 'params[0]'): 'object_or_string'}


def parse_conversion_rows(text):
    """Preserve both flags discarded by the maintained triple comparison."""
    marker = 'static const CRPCConvertParam vRPCConvertParams[] ='
    if text.count(marker) != 1:
        raise ValueError('Missing or ambiguous conversion table')
    body = text.split(marker, 1)[1]
    if '\n};' not in body:
        raise ValueError('Unclosed conversion table')
    rows = []
    pattern = re.compile(r'\{\s*"([^"]*)",\s*(\d+)\s*,\s*"([^"]*)"\s*'
                         r'(?:,\s*(true|false)\s*(?:,\s*(true|false)\s*)?)?\}')
    for line in body.split('\n};', 1)[0].splitlines():
        if '{' not in line or '"' not in line:
            continue
        clean = re.sub(r'/\*.*?\*/', '', line)
        match = pattern.search(clean)
        if not match:
            raise ValueError('Unparsed conversion row: ' + line)
        method, index, name, also_string, json_object = match.groups()
        rows.append((method, int(index), name,
                     'object_or_string' if json_object == 'true' else
                     'json_or_string' if also_string == 'true' else 'json'))
    if not rows:
        raise ValueError('Empty conversion table')
    return rows


def _argument(arg):
    keys = {'names', 'type', 'per_name_types', 'skip', 'also_positional',
            'hidden', 'optional', 'inner'}
    if not isinstance(arg, dict) or set(arg) != keys:
        raise ValueError('Incomplete argument record')
    if not isinstance(arg['names'], str) or not all(arg['names'].split('|')):
        raise ValueError('Invalid argument names')
    if arg['type'] not in TYPES or not isinstance(arg['per_name_types'], list):
        raise ValueError('Unknown argument type')
    if any(t not in TYPES for t in arg['per_name_types']):
        raise ValueError('Unknown per-name argument type')
    if arg['per_name_types'] and len(arg['per_name_types']) != len(arg['names'].split('|')):
        raise ValueError('Per-name types do not match aliases')
    if arg['per_name_types'] and arg['type'] != arg['per_name_types'][0]:
        raise ValueError('Primary type disagrees with per-name declarations')
    if any(type(arg[k]) is not bool for k in ['skip', 'also_positional', 'hidden', 'optional']):
        raise ValueError('Invalid argument flags')
    if not isinstance(arg['inner'], list):
        raise ValueError('Invalid inner declarations')
    for child in arg['inner']:
        _argument(child)


def _registry(records, findings):
    groups = {}
    for entry in records:
        method = entry.get('method') if isinstance(entry, dict) else None
        binding = str(method or '<registration>')
        try:
            if set(entry) != {'method', 'handler_index', 'canonical', 'status', 'routing', 'arguments'}:
                raise ValueError('Incomplete registration record')
            if not isinstance(method, str) or not method or (not isinstance(entry['canonical'], str) or not entry['canonical']):
                raise ValueError('Invalid registration identity')
            if type(entry['handler_index']) is not int or entry['handler_index'] < 0:
                raise ValueError('Invalid handler position')
            if entry['status'] not in STATUSES or not isinstance(entry['routing'], list):
                raise ValueError('Invalid metadata status or routing')
            for route in entry['routing']:
                if (not isinstance(route, list) or len(route) != 2 or
                        not isinstance(route[0], str) or type(route[1]) is not bool):
                    raise ValueError('Invalid routing entry')
            if entry['status'] != 'AVAILABLE':
                if entry['arguments'] is not None:
                    raise ValueError('Unavailable declaration must not look like zero arguments')
            else:
                if not isinstance(entry['arguments'], list):
                    raise ValueError('Available declaration has no argument list')
                routing = []
                for arg in entry['arguments']:
                    _argument(arg)
                    if arg['type'] == 'OBJ_NAMED_PARAMS':
                        routing.extend([child['names'], True] for child in arg['inner'])
                    routing.append([arg['names'], False])
                if routing != entry['routing']:
                    raise ValueError('Declared arguments disagree with registered routing')
            groups.setdefault(method, []).append(entry)
        except (ValueError, TypeError, KeyError) as error:
            findings.append(Finding('invalid_metadata', binding, str(error)))
    for method, entries in groups.items():
        indices = [e['handler_index'] for e in entries]
        if indices != list(range(len(entries))):
            findings.append(Finding('invalid_metadata', method, 'Missing, duplicated or reordered handler slot'))
    return groups


def _resolve(arguments, form, selector):
    if form == 'positional':
        if type(selector) is not int or not 0 <= selector < len(arguments):
            return None
        arg = arguments[selector]
        return f'params[{selector}]', arg, arg['per_name_types'] or [arg['type']]
    # Dispatch consumes promoted named-only fields before their parent aliases.
    # Ordinary nested objects never promote their own children to top level.
    for index, arg in enumerate(arguments):
        if arg['type'] == 'OBJ_NAMED_PARAMS':
            for child in arg['inner']:
                names = child['names'].split('|')
                if selector in names:
                    types = child['per_name_types']
                    return f'params[{index}].{selector}', child, types or [child['type']]
        names = arg['names'].split('|')
        if selector in names:
            types = arg['per_name_types']
            return f'params[{index}]', arg, types or [arg['type']]
    return None


def consume(document, contracts, conversion_rows):
    findings = []
    try:
        if (not isinstance(contracts, dict) or type(contracts.get('schema')) is not int or
                contracts['schema'] != 1 or not isinstance(contracts.get('probes'), list) or
                not isinstance(contracts.get('metadata_rules'), list) or
                not isinstance(contracts.get('selected_methods'), list)):
            raise ValueError('Unsupported contract schema')
        referenced = set()
        for row in contracts['probes']:
            if (not isinstance(row, dict) or not set(Probe.__dataclass_fields__).issubset(row) or
                    row.get('scope') not in ['converter_only', 'declared_input'] or
                    type(row.get('opaque_contract')) is not bool or
                    not isinstance(row['method'], str) or not row['method'] or record_error(row['expected'])):
                raise ValueError('Incomplete or malformed probe contract')
            referenced.add(row['method'])
        rule_methods = []
        for rule in contracts['metadata_rules']:
            if (not isinstance(rule, dict) or set(rule) != {'method', 'schema'} or
                    not isinstance(rule['method'], str) or not rule['method'] or
                    rule['schema'] not in ['zero_arguments', 'opaque']):
                raise ValueError('Unknown metadata rule')
            rule_methods.append(rule['method'])
        referenced.update(rule_methods)
        selected = contracts['selected_methods']
        if (not referenced or any(not isinstance(m, str) or not m for m in selected) or
                len(set(selected)) != len(selected) or set(selected) != referenced or
                len(set(rule_methods)) != len(rule_methods)):
            raise ValueError('Contract selection is empty, duplicated or incomplete')
    except (ValueError, TypeError, KeyError) as error:
        return [Finding('invalid_contract', '<contracts>', str(error))]
    if not isinstance(document, dict) or set(document) != {'schema', 'registrations', 'conversions'} or type(document['schema']) is not int or document['schema'] != 1:
        return [Finding('invalid_metadata', '<document>', 'Unsupported native record schema')]
    if not isinstance(document['registrations'], list) or not isinstance(document['conversions'], list):
        return [Finding('invalid_metadata', '<document>', 'Native record arrays are missing')]
    groups = _registry(document['registrations'], findings)
    for method in set(groups) - set(contracts['selected_methods']):
        findings.append(Finding('invalid_metadata', method, 'Outside the selected native inventory'))
    observations = {}
    for record in document['conversions']:
        try:
            if set(record) != {'method', 'form', 'selector', 'raw', 'result'}:
                raise ValueError('Incomplete conversion record')
            method, form, selector, raw = (record[k] for k in ['method', 'form', 'selector', 'raw'])
            if (not isinstance(method, str) or not isinstance(raw, str) or
                    form not in ['named', 'positional'] or
                    (form == 'named' and (not isinstance(selector, str) or not selector)) or
                    (form == 'positional' and (type(selector) is not int or selector < 0))):
                raise ValueError('Invalid conversion identity')
            error = record_error(record['result'])
            if error:
                raise ValueError(error)
            key = method, form, selector, raw
            if key in observations:
                raise ValueError('Duplicate conversion observation')
            observations[key] = record['result']
        except (ValueError, TypeError, KeyError) as error:
            findings.append(Finding('invalid_observation', '<conversion>', str(error)))
    probes = [Probe(**{k: row[k] for k in Probe.__dataclass_fields__}) for row in contracts['probes']]
    # Conversion findings survive unavailable/ambiguous declarations independently.
    findings.extend(compare(probes, observations))
    positional, named = {}, {}
    for method, index, name, mode in conversion_rows:
        positional.setdefault((method, index), mode)
        named.setdefault((method, name), mode)
    simple_types = {'OBJ': 1, 'OBJ_NAMED_PARAMS': 1, 'OBJ_USER_KEYS': 1,
                    'ARR': 2, 'STR': 3, 'STR_HEX': 3, 'NUM': 4, 'BOOL': 5}
    for row, probe in zip(contracts['probes'], probes):
        binding = f'{probe.method}/{probe.form}/{probe.selector}->{probe.destination}'
        modes = named if probe.form == 'named' else positional
        actual_mode = modes.get((probe.method, probe.selector), 'literal')
        if actual_mode != probe.mode:
            findings.append(Finding('conversion_mode_mismatch', binding,
                                    f'Expected {probe.mode}; client source declares {actual_mode}'))
        entries = groups.get(probe.method, [])
        if not entries:
            findings.append(Finding('unresolved', binding, 'No invoked registration'))
        for entry in entries:
            target = binding + f'/handler[{entry["handler_index"]}]'
            if entry['status'] != 'AVAILABLE':
                findings.append(Finding('unresolved', target, entry['status']))
                continue
            resolved = _resolve(entry['arguments'], probe.form, probe.selector)
            if resolved is None:
                findings.append(Finding('binding_mismatch', target, 'No registered argument for selector'))
                continue
            destination, arg, types = resolved
            if destination != probe.destination:
                findings.append(Finding('binding_mismatch', target, f'Registered route is {destination}'))
            if row['scope'] == 'converter_only':
                continue
            if row['scope'] != 'declared_input':
                findings.append(Finding('invalid_contract', target, 'Unknown comparison scope'))
                continue
            if arg['skip']:
                if not (row['opaque_contract'] and types == ['STR'] and
                        SOURCE_UNIONS.get((probe.method, destination)) == probe.mode):
                    findings.append(Finding('unresolved', target, 'Skipped type check has no selected source-backed contract'))
                    continue
                allowed = {1, 3}
            elif any(t not in simple_types for t in types):
                findings.append(Finding('unresolved', target, 'No selected conversion policy for declaration type'))
                continue
            else:
                allowed = {simple_types[t] for t in types}
            # MatchesType's optional-null shortcut is a top-level rule; a
            # promoted inner field may have a separate handler type check.
            if arg['optional'] and '.' not in destination:
                allowed.add(0)
            if probe.expected.get('type') not in allowed:
                findings.append(Finding('declaration_mismatch', target, 'Expected input type is not declared by this binding'))
    triples = [tuple(r[:3]) for r in conversion_rows]
    for rule in contracts['metadata_rules']:
        entries = groups.get(rule['method'], [])
        if not entries:
            findings.append(Finding('unresolved', rule['method'], 'No invoked registration'))
        for entry in entries:
            if entry['status'] != 'AVAILABLE':
                findings.append(Finding('unresolved', rule['method'] + f'/handler[{entry["handler_index"]}]', entry['status']))
            else:
                for finding in metadata_findings(rule['method'], len(entry['arguments']), rule['schema'], triples):
                    findings.append(Finding(finding.kind, finding.binding + f'/handler[{entry["handler_index"]}]', finding.detail))
    return list(dict.fromkeys(findings))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records', type=Path, required=True)
    parser.add_argument('--client-source', type=Path, required=True)
    parser.add_argument('--contracts', type=Path, default=Path(__file__).with_name('contracts.json'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    findings = consume(json.loads(args.records.read_text()), json.loads(args.contracts.read_text()),
                       parse_conversion_rows(args.client_source.read_text()))
    args.output.write_text(json.dumps({'selected_contracts_only': True, 'full_rpc_help_green': False,
                                     'findings': [asdict(f) for f in findings]}, indent=2) + '\n')
    print(f'{len(findings)} selected findings; full RPC-help acceptance remains separate')
    return int(bool(findings))


if __name__ == '__main__':
    raise SystemExit(main())
