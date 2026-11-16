"""Strict offline interpretation of a maintained Boost XML result."""
import re
import xml.etree.ElementTree as ET


def classify(expected, log, report, exit_code, budget_stop=None):
    expected = set(expected)
    matches = re.findall(r'Running (\d+) test cases?', log)
    announced = int(matches[0]) if len(matches) == 1 else None
    result = dict(exit=exit_code, expected=len(expected), announced=announced,
                  cases={}, budget_stop=budget_stop, state='incomplete')
    if report:
        try:
            root = ET.fromstring(report)
            def walk(node, parents=()):
                if node.tag == 'TestSuite':
                    parents += (node.attrib['name'],)
                if node.tag == 'TestCase':
                    path = '/'.join(parents[1:] + (node.attrib['name'],))
                    assert path not in result['cases'], 'Duplicate reported case'
                    result['cases'][path] = dict(node.attrib)
                for child in node:
                    walk(child, parents)
            walk(root)
        except (ET.ParseError, AssertionError, KeyError) as ex:
            result['report_error'] = str(ex)
    if budget_stop:
        result['state'] = 'timeout' if budget_stop == 'TIME_BUDGET' else 'resource_stop'
    elif (result.get('report_error') or announced != len(expected) or not expected <= set(result['cases']) or
          any(result['cases'][k].get('result') != 'skipped' for k in set(result['cases']) - expected)):
        result['state'] = 'selection_or_report_incomplete'
    elif exit_code == 0 and all(result['cases'][k].get('result') == 'passed' for k in expected):
        result['state'] = 'passed'
    elif any(x.get('result') in ('failed', 'aborted') for x in result['cases'].values()):
        result['state'] = 'failed'
    return result
