"""Record six supplemental maps as a separate future scope; do not traverse."""
from pathlib import Path
import importlib.util,json
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('world_assets',HERE/'trace-world-assets.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
inventory=a.read(HERE/'all-map-inventory.json');baseline=a.read(a.RESULT)
covered={n['package'] for n in baseline['nodes']};maps=[];edges=[]
for i,m in enumerate(inventory['supplementalMaps']):
    doc=a.read(Path(m['decoded']));edges.extend(e for e in a.imports(doc,m['package'],Path(m['decoded'])) if e['followed'])
    maps.append({'package':m['package'],'pakPath':m['pakEntry'],'decodedFile':m['decoded'],'decodedSha256':m['decodedSha256'],
        'sourceFiles':m['sourceFiles'],'allMapInventoryPointer':f'/supplementalMaps/{i}',
        'externalReferenceEvidencePointer':f'/supplementalMaps/{i}/externalExactReferences','externalExactReferenceCount':len(m.get('externalExactReferences',[])),
        'status':'resource-recursion-pending-separate-scope','unusedClaim':False,'runtimeUseProven':m['runtimeUseProven']})
packages=sorted({e['to'] for e in edges})
result={'scope':'Six supplemental map roots; distinct from the completed 35-map scope. Exact resource imports queued for later recursion only.',
    'allMapInventoryFile':str(HERE/'all-map-inventory.json'),'allMapInventorySha256':a.sha(HERE/'all-map-inventory.json'),
    'baselineWorldCoverageSha256':baseline['provenance']['worldCoverageSha256'],'baselineClosureFile':str(a.RESULT),
    'baselineQueueExhausted':baseline['statistics']['queueExhausted'],'currentWorldMaps':35,'additionalMapCount':len(maps),
    'additionalMapSeeds':maps,'rootEdges':edges,'resourceSeedPackages':packages,
    'alreadyRecordedIn35MapClosure':[p for p in packages if p in covered],'additionalNotYetRecordedResourceSeeds':[p for p in packages if p not in covered],
    'automaticTraversalAuthorizedForThisRun':False,'limitations':['No recursion from these six maps performed by this task.','Blueprint-owned mesh defaults may not appear directly in map Imports; combine with logic closure.','Some Test-named maps have actual gameplay bytecode references; names are not grounds to exclude them.','A static call-site/reference does not prove a captured play session loaded the map.'],
    'resumeSteps':['Freeze the 35-map baseline denominator.','Traverse this resourceSeedPackages list with existing cache into an additional-6-map result.','Record overlap and newly reached packages separately; follow allMapInventory pointers to activation evidence.']}
a.write(HERE/'remaining-map-asset-seeds.json',result)
print(json.dumps({'additionalMaps':len(maps),'resourceSeeds':len(packages),'alreadyIn35':len(result['alreadyRecordedIn35MapClosure']),'newSeeds':len(result['additionalNotYetRecordedResourceSeeds'])}))
