"""Summarize actual retained REA responses; never substitutes UE parser output."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent
responses = root / 'session-focused/responses'
def evidence(name):
    response = json.loads((responses / name).read_text(encoding='utf8'))
    assert not response.get('error') and not response['result'].get('isError')
    return response['result']['structuredContent']

overview = evidence('003-overview.json')
registration = evidence('015-registration-bytes.json')
raw = bytes.fromhex(registration['normalized_result']['bytes_hex'])
bindings = []
for offset, name in [(0, 'FinishActivity'), (16, 'GetActivityID'), (32, 'SetEnableActivity'), (48, 'StartActivity')]:
    bindings.append({'name': name, 'namePointer': hex(int.from_bytes(raw[offset:offset+8], 'little')), 'functionPointer': hex(int.from_bytes(raw[offset+8:offset+16], 'little')), 'tableAddress': hex(0x1438e8b30 + offset), 'evidenceId': registration['evidence_id']})
functions = []
out = root / 'native-functions'
out.mkdir(exist_ok=True)
for path in sorted(responses.glob('*-analyze-*.json')):
    ev = evidence(path.name)
    value = ev['normalized_result']
    address = value['procedure']['address']
    (out / (address + '.pseudo.c')).write_text(value['pseudocode'].replace('\r\n', '\n'), encoding='utf8')
    (out / (address + '.asm.txt')).write_text('\n'.join(value['assembly']), encoding='utf8')
    functions.append({'address': address, 'evidenceId': ev['evidence_id'], 'response': str(path.relative_to(root)), 'body': value['procedure']['body'], 'callees': [x['address'] for x in value['callees']], 'unresolvedCalls': value['unresolved_calls'], 'limitations': value['limitations']})

report = {
    'scope': 'Initial focused native investigation; NOT full native semantic recovery or a complete Web port.',
    'source': overview['subject'],
    'provider': overview['analysis_profile']['parameters']['upstream_analysis_profile'],
    'inventory': overview['normalized_result'],
    'overviewEvidenceId': overview['evidence_id'],
    'inventoryLimitations': overview['limitations'],
    'functionPointerTable': bindings,
    'analyzedFunctions': functions,
    'activityIdMapping': {'0': 'UNDEFEATED_SubTask1', '1': 'UNDEFEATED_SubTask2', '2': 'UNDEFEATED_SubTask3', '3': 'UNDEFEATED_SubTask4', '4': 'UNDEFEATED_MainActivity'},
    'mappingEvidenceId': evidence('013-analyze-activity-id-body.json')['evidence_id'],
    'mappingStatus': 'Derived from static decompilation and assembly; not runtime-observed.',
    'bundle': 'native-evidence-expanded.json',
    'defaultAttempt': {'status': 'provider_timeout', 'deadlineMs': 1800000, 'response': 'session/responses/003-overview.json'},
    'limitations': ['Four costly analyzers disabled in successful profile; profile digest retained.', 'Function/string inventory counts do not mean those items have been semantically understood.', 'Indirect OnlineSubsystem targets and runtime dispatch remain unresolved.', 'No original game launch or behavior comparison was performed.', 'Native pseudocode is inferred decompiler output, not recovered original source.'],
}
(root / 'native-analysis.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
prov = json.loads((root / 'toolchain-provenance.json').read_text(encoding='utf8'))
prov['focusedAnalysisAttempt']['status'] = 'initial_queries_succeeded'
prov['focusedAnalysisAttempt']['overviewEvidenceId'] = overview['evidence_id']
prov['focusedAnalysisAttempt']['analyzedFunctions'] = len(functions)
(root / 'toolchain-provenance.json').write_text(json.dumps(prov, ensure_ascii=False, indent=2), encoding='utf8')
print(json.dumps({'functionsAnalyzed': len(functions), 'inventoryFunctions': report['inventory']['procedure_count'], 'inventoryDefinedStrings': report['inventory']['string_count'], 'bindings': bindings}, ensure_ascii=False))
