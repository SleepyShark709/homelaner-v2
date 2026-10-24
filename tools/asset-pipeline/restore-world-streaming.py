"""Publish an evidence-bounded original-world streaming contract.

Reads prior UAssetAPI decodes only. Does not run the game, unpack the install,
or modify world geometry/materials. Kismet offsets come from the installed
UAssetAPI serializer; they are checked against each serialized function size.
This is UE static reconstruction, not native REA or observed runtime evidence.
"""
from pathlib import Path
import ast, hashlib, json, re

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / 'research'
OUT = ROOT / 'public/assets/world/streaming-manifest.json'

def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        while b := f.read(1048576): h.update(b)
    return h.hexdigest()

def write(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')

# Reuse the already-reviewed streaming JSON reader and property unwrapping;
# do not import/execute the terrain exporter.
helpers = {'json': json, 're': re}
tree = ast.parse((ROOT / 'tools/asset-pipeline/restore-world-terrain.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)
    and n.name in ['array_items', 'val', 'props']], type_ignores=[]), 'property_helpers', 'exec'), helpers)
array_items, props = helpers['array_items'], helpers['props']
coverage = read(RESEARCH / 'rea-audit/all-blueprint-coverage.json')
class_paths = {p['package'].split('/')[-1]: Path(p['decoded_path'])
               for p in coverage['packages'] if p.get('decoded_path')}
names = ['HeroGameMode', 'BP_CityManager', 'BP_StoryManager', 'HeroGameInstance',
         'BP_ChallengQuestSpawnPoint', 'BP_StoryStartPoint']
views, sources, checks = {}, {}, []
for name in names:
    views[name] = read(RESEARCH / f'streaming-{name}-view.json')
    offsets = read(RESEARCH / f'streaming-{name}-offsets.json')
    assert all(x['computedSize'] == x['declaredSize'] for x in offsets), name
    sources[name] = {'path': str(class_paths[name]), 'sha256': sha(class_paths[name]),
                     'offsets': str(RESEARCH / f'streaming-{name}-offsets.json')}
    checks.append({'class': name, 'functions': len(offsets), 'allFunctionByteSizesMatch': True})

def stmt(name, index, export=0):
    f = next(f for f in views[name] if f['export_index'] == export)
    return f['statements'][index]

def proof(name, indices, export=0):
    return [{'source': name, 'function': next(f['name'] for f in views[name] if f['export_index'] == export),
             **stmt(name, i, export)} for i in indices]

def defaults(name, export):
    return props(read(class_paths[name])['Exports'][export])

world = read(RESEARCH / 'rea-audit/world-coverage.json')
maps = read(RESEARCH / 'rea-audit/all-map-inventory.json')
table = read(RESEARCH / 'rea-audit/mainlevel-streaming-table.json')
main = next(m for m in world['levels'] if m['name'] == 'MainLevel')
sources['MainLevel'] = {'path': main['decoded'], 'sha256': main['decodedSha256']}
sources['PlayerBP'] = {'path': str(class_paths['PlayerBP']), 'sha256': sha(class_paths['PlayerBP'])}
map_by_name = {m['package'].split('/')[-1]: m['package'] for m in maps['allMaps']}
records = {r['package'].split('/')[-1]: r for r in table['records']}
always = [n for n, r in records.items() if r['class'] == 'LevelStreamingAlwaysLoaded']
assert set(always) == {'CitizenWayPoint', 'LightingTest', 'CustomEventLevel', 'TitleMenuLevel'}
gm_defaults = defaults('HeroGameMode', 76)
assert gm_defaults['MainLevelName'] == 'MainLevel' and gm_defaults['DynamicPropsLevelName'] == 'DynamicProps'

# Recover request order from the actual latent completion linkage, not export order.
by_offset = {s['offset']: s for s in views['HeroGameMode'][0]['statements']}
startup, offset = [], 24124
while True:
    s = by_offset[offset]; call = s['ast']
    assert call['call'] == 'LoadStreamLevel' and call['args'][2:4] == [True, False]
    arg = call['args'][1]
    level = gm_defaults[arg] if arg == 'DynamicPropsLevelName' else arg
    resume = call['args'][4]['Value'][0]['Value']
    startup.append({'levelName': level, 'package': map_by_name[level], 'makeVisibleAfterLoad': True,
                    'shouldBlockOnLoad': False, 'onCompletedResumeOffset': resume,
                    'evidence': {'source': 'HeroGameMode', **s}})
    if level == 'DynamicProps': break
    offset = resume
assert [s['levelName'] for s in startup] == ['DownTown','Park','FinancialDistrict','CommercialArea',
    'IndustrialArea','Beach','Slam','ResidentialArea1','ResidentialArea2','ResidentialArea3','Coast','DynamicProps']
baseline_names = ['MainLevel'] + always + [s['levelName'] for s in startup]
assert len(set(baseline_names)) == 17

# Enum identities are actual EnumExport integer assignments, not NewEnumerator suffixes.
enums = {}
for name in ['E_ChallengeQuestDifficulty', 'E_ChallengeQuestType', 'E_Story']:
    paths = list((RESEARCH / 'rea-audit/decoded').rglob(name + '.json'))
    if not paths: continue
    p = paths[0]; d = read(p); e = next(e for e in d['Exports'] if 'Enum' in e)
    labels = {k['Value']: v.get('CultureInvariantString') for prop in e.get('Data', [])
              if prop['Name'] == 'DisplayNameMap' for k, v in prop['Value']}
    enums[name] = {'source': str(p), 'sha256': sha(p), 'pointer': '/Exports/0/Enum/Names',
                  'values': [{'serializedName': n['Item1'], 'value': n['Item2'],
                              'displayName': labels.get(n['Item1'].split('::')[-1])} for n in e['Enum']['Names']]}
enum_lookup = {n['serializedName']: n['value'] for e in enums.values() for n in e['values']}
cq = defaults('BP_ChallengQuestSpawnPoint', 46)
for name, export, radius in [('BP_ChallengQuestSpawnPoint',69,256.),
                             ('BP_ChallengQuestSpawnPoint',70,2000.),
                             ('BP_StoryStartPoint',23,200.)]:
    component_defaults = defaults(name, export)
    assert component_defaults['SphereRadius'] == radius
    assert not set(component_defaults) & {'RelativeLocation','RelativeRotation','RelativeScale3D'}, \
        'Template transform needs composition before publishing trigger coordinates'
story_data = read(class_paths['BP_StoryManager'])['Exports'][26]['Data'][1]
story_mapping = [{'storyType':enum_lookup[k['EnumValue']], 'levelName':v['Value'],
                  'package':map_by_name[v['Value']]} for k,v in story_data['Value']]
assert [x['storyType'] for x in story_mapping] == [0,1,2,3]
cq_mapping = []
for typ, field in [(0, 'QuestLevelNameD'), (1, 'QuestLevelNameF')]:
    for difficulty, level in enumerate(cq[field]):
        cq_mapping.append({'questType': typ, 'difficulty': difficulty, 'levelName': level,
                           'package': map_by_name.get(level), 'shippedPackageExists': level in map_by_name,
                           'registeredInMainWorld': level in records})

# MainLevel instances and their own component overrides. Default radii are only
# applied when the serialized component did not override them.
detail = read(RESEARCH / 'rea-audit/levels/MainLevel.json')
trigger_actors = [a for a in detail['actors'] if a['class'] in
                  ['BP_ChallengQuestSpawnPoint_C', 'BP_StoryStartPoint_C']]
wanted = {a['exportIndex'] for a in trigger_actors}
wanted.update(c['exportIndex'] for c in detail['componentTransforms'] if c['sourceActorExportIndex'] in wanted)
selected = {i+1: e for i, e in enumerate(array_items(Path(main['decoded']), 'Exports')) if i+1 in wanted}
imports = list(array_items(Path(main['decoded']), 'Imports'))
world_scan = read(RESEARCH / 'streaming-map-scan.json')
world_setting = world_scan['maps'][0]['worldSettings'][0]
game_mode_import = imports[-world_setting['properties']['DefaultGameMode']-1]
assert game_mode_import['ObjectName'] == 'HeroGameMode_C'
trigger_instances = []
for a in trigger_actors:
    ap = props(selected[a['exportIndex']]); is_cq = a['class'] == 'BP_ChallengQuestSpawnPoint_C'
    radius_defaults = {'MainSphere': 256., 'TutorialSphere': 2000.} if is_cq else {'Sphere': 200.}
    inst = {'id': a['name'], 'class': a['class'], 'package': main['package'],
            'sourcePointer': f"/Exports/{a['exportIndex']-1}", 'serializedProperties': ap,
            'contract': 'challenge-entry' if is_cq else 'story-entry', 'volumes': []}
    if is_cq:
        struct = {**cq['ChallengeQuestStruct'], **ap.get('ChallengeQuestStruct', {})}
        typ = enum_lookup[next(v for k,v in struct.items() if k.startswith('QuestType_'))]
        difficulty = enum_lookup[next(v for k,v in struct.items() if k.startswith('QuestDifficulty_'))]
        inst.update(questType=typ, difficulty=difficulty,
                    levelName=next(x['levelName'] for x in cq_mapping if x['questType']==typ and x['difficulty']==difficulty))
    else:
        inst['storyType'] = enum_lookup.get(ap.get('StoryType'))
    for c in detail['componentTransforms']:
        if c['sourceActorExportIndex'] != a['exportIndex'] or c['component'] not in radius_defaults: continue
        cp = props(selected[c['exportIndex']]); t = c['composedComponentTransformUE']
        radius = cp.get('SphereRadius', radius_defaults[c['component']]); pos = t['position']
        scale = t['scale']; assert len(set(scale)) == 1, 'nonuniform sphere scale needs UE min-axis handling'
        inst['volumes'].append({'component': c['component'], 'shape': 'sphere', 'positionUE': pos,
            'position': [pos[0]/100, pos[2]/100, pos[1]/100], 'localRadiusUE': radius,
            'radius': float(radius)*abs(scale[0])/100, 'scale': scale,
            'radiusSource': 'instance-override' if 'SphereRadius' in cp else 'Blueprint-component-template',
            'componentPointer': f"/Exports/{c['exportIndex']-1}", 'serializedProperties': cp,
            'overlapPurpose': 'tutorial-event' if c['component']=='TutorialSphere' else 'set-interaction-prompt',
            'autoLoadLevelOnEntry': False,
            'runtimeEnabledState': 'gated by Blueprint state; not observed at runtime'})
    trigger_instances.append(inst)

conditional = [{'levelName': 'EnelightMeteor', 'package': map_by_name['EnelightMeteor'],
    'condition': 'HeroGameInstance.SaveData.IsFirstPlayerSpecialAction == true',
    'stage': 'after DynamicProps completion, before loading-finished widgets',
    'evidence': proof('HeroGameMode', [25,26,27,53])}]
events = [
    {'id':'tutorial', 'loadEntry':'HeroGameInstance.LoadTutorial', 'unloadEntry':'HeroGameInstance.UnloadTutorial',
     'levelName':'TutorialLevel', 'package': map_by_name['TutorialLevel'],
     'automaticStartCondition':'HeroGameMode.GameStartEvent: NOT SaveData.IsFirstTutorial; ForceStartTutorial is also an explicit entry',
     'evidence':proof('HeroGameMode',[1228,1229,1230,1231,82,83,84])+proof('HeroGameInstance',[124,126,128,129,131]),
     'unknown':'saved flag initial value and current user save state are not assumed'},
    {'id':'challenge', 'loadEntry':'StartOrEndCQ(IsStart?=true,CQType,CQDifficulty) -> matching instance.StartCQEvent',
     'entryGuard':'own QuestType == CQType AND own QuestDifficulty == CQDifficulty',
     'mainWorldTransition':'StartCQEvent -> LoadingNow=true -> unload selected level -> completion -> unload selected level again -> completion -> load selected level visible=true/block=false',
     'nonMainWorldTransition':'IsMainLevel=false selects DPropTest for QuestType=0, FPropTest for QuestType=1; not part of MainLevel baseline',
     'mapping':cq_mapping,
     'evidence':proof('BP_ChallengQuestSpawnPoint',list(range(0,12)),36)
        +proof('BP_ChallengQuestSpawnPoint',[518,519,521,523,526,527,528,529,531,533,461,280,281,271,272,266,267,141,142,143,96,97,145,146,147,148,150,152,100,103]),
     'unloadEvidence':proof('BP_ChallengQuestSpawnPoint',[248,250,259,446,453,455]),
     'unknown':'EndCQEvent/Restart/result-screen animation ordering and all reset side effects are preserved in AST, not fully converted to an executable event graph'},
    {'id':'story', 'loadEntry':'BP_StoryManager.StartStory(StoryType)',
     'mapping':story_mapping,
     'beforeLoad':['CurrentStoryType=argument','AddLoadScreen','HeroGameState.EndContent_Event','SetInputState(0)'],
     'unloadEntries':['ForceEndStory','ClearStory'],
     'evidence':proof('BP_StoryManager',list(range(305,318))+[323]),
     'mappingSource':{'source':'BP_StoryManager','pointer':'/Exports/26/Data/1'},
     'unknown':'all save/progression conditions enabling each story entrance are not yet fully reconstructed'},
    {'id':'boss', 'loadEntry':'BPFL_BossSpawn.BossSpawn(BossType) -> first BP_CityManager.LoadBossLevel(BossType)',
     'guards':['HeroGameMode.GameInputState == 4','first GetAllActorsOfClass(BP_BaseBoss) result is invalid'],
     'mapping':[{'bossType':i,'mainWorldLevelName':n,'nonMainWorldLevelName':t,
                 'package':map_by_name.get(n),'shippedPackageExists':n in map_by_name}
                for i,n,t in [(0,'WindBossLevel','TestBossLevelWind'),(1,'FireBossLevel','TestBossLevelFire'),
                              (2,'LightningBossLevel','TestBossLevelLightning'),(3,'BotBottLevel','TestBossLevelBot'),(4,'None','None')]],
     'unloadEntry':'BP_CityManager.UnloadBossLevel(BossType), guarded by first BP_BaseBoss being valid',
     'evidence':proof('BP_CityManager',list(range(102,125))+list(range(2,21))),
     'unknown':'automatic boss event scheduling/threshold timing upstream in HeroGameState is not fully contracted; do not spawn all bosses on initial load'},
    {'id':'dynamic-props-reset', 'transition':'Unload DynamicProps then latent completion at 2314 reloads it; not permanent district eviction',
     'evidence':proof('HeroGameMode',[318,319,320,321,80])}
]
trigger_contracts = [
    {'id':'challenge-entry', 'mainSphereRadiusUE':256, 'tutorialSphereRadiusUE':2000,
     'mainOverlapGuard':['OtherActor.ActorHasTag(Player)','first BP_BaseBoss invalid','Deactive == false',
                         'if Tutorial then own difficulty == 5','GameInputState in [0,4] for panel display'],
     'mainOverlapEffect':'SetStartMassageTypeAndStoryType(0,0); show CQ panel and publish CQSetting(self); no LoadStreamLevel here',
     'exitEffect':'SetStartMassageTypeAndStoryType(3,0); hide CQ panel when GameInputState in [0,4]; CQSetting(null)',
     'evidence':proof('BP_ChallengQuestSpawnPoint',list(range(473,483))+list(range(70,80))+[90,483,484,485,489,490,501]),
     'radiusEvidence':[{'source':'BP_ChallengQuestSpawnPoint','pointer':'/Exports/69/Data/0'},
                       {'source':'BP_ChallengQuestSpawnPoint','pointer':'/Exports/70/Data/0'}],
     'tutorialSphereBeginContract':'If GameMode.InTutorial, NOT OverlapEffect, P_QuestArea1.IsActive, and OtherActor has Player tag: deactivate P_QuestArea1; OverlapEffect=true. No level load on this begin-overlap path.',
     'tutorialSphereEvidence':proof('BP_ChallengQuestSpawnPoint',list(range(714,724))+[731]),
     'tutorialSphereUnknown':'remaining tutorial end-overlap and progression effects are not fully contracted'},
    {'id':'story-entry', 'sphereRadiusUE':200,
     'overlapGuard':['OtherActor.ActorHasTag(Player)','GameInputState == 4'],
     'effect':'SetStartMassageTypeAndStoryType(IsSotryClear ? 2 : 1, StoryType) and show prompt. No direct streaming call.',
     'exitEffect':'SetStartMassageTypeAndStoryType(3,4) and hide prompt',
     'interactionDispatch':'PlayerBP StartMassageType=1 calls StoryManager.StartStory(StoryType); type=2 calls BossSpawn using StoryType 1->0,2->1,3->2',
     'evidence':proof('BP_StoryStartPoint',list(range(96,115))+[124,125,126]),
     'radiusEvidence':{'source':'BP_StoryStartPoint','pointer':'/Exports/23/Data/0'},
     'dispatchSource':{'source':str(class_paths['PlayerBP']),'pointers':['/Exports/0/ScriptBytecode/469','/Exports/0/ScriptBytecode/471','/Exports/0/ScriptBytecode/490']},
     'unknown':'input action key and complete outer input guard not re-traced in this bounded streaming contract; overlap activation also depends on story progression'}
]
inventory = read(RESEARCH / 'streaming-call-inventory.json')
call_counts = {n:sum(c['ast']['call']==n for c in inventory['calls']) for n in ['LoadStreamLevel','UnloadStreamLevel']}
unconfirmed_nested = [r for r in world['nestedStreamingReferences'] if r['sourcePackage'] != main['package']]
manifest = {
    'schemaVersion':1, 'status':'original-static-streaming-contract-not-runtime-observation',
    'coordinateSystem':{'originUE':[0,0,0],'positionConversion':'[UE.x, UE.z, UE.y] / 100'},
    'provenance':{'method':'UAssetAPI decoded Blueprint expressions + exact Kismet VM offsets + serialized World table',
                  'isNativeREAOutput':False,'originalGameExecuted':False,'sourceHashes':sources},
    'entry':{'package':main['package'],'gameMode':'HeroGameMode_C','worldSettingsPointer':'/Exports/11844/Data',
             'configKey':'[/Script/EngineSettings.GameMapsSettings] GameDefaultMap=/Game/-HeroGame/Maps/MainLevel.MainLevel'},
    'baseline':{'stage':'MainLevel startup loading chain complete, before optional tutorial/story/challenge/boss events',
        'levelNames':baseline_names,'packages':[map_by_name[n] for n in baseline_names],
        'persistentLevel':'MainLevel','alwaysLoadedLevelNames':always,
        'requestedVisibleLevelNames':[s['levelName'] for s in startup],
        'visibilityMeaning':'level load/visibility policy only; individual actors may hide/activate through Blueprint',
        'notPermanentClaim':'district startup loads proven; DynamicProps is later reset and actor visibility can change',
        'excludeByDefault':[n for n in records if n not in baseline_names],
        'evidence':proof('HeroGameMode',[821,822,823,824,825,826,827,829,913]),
        'worldTableSource':'research/rea-audit/mainlevel-streaming-table.json'},
    'startupSequence':startup,
    'transitionOverlay':{'levelName':'LoadLevel','onLoadedDelaySeconds':1,
        'then':'UnloadStreamLevel(LoadLevel,block=false)',
        'completionRelation':'independent latent branch; no claim that this waits for all city sublevels',
        'evidence':proof('HeroGameMode',[830,58,56])},
    'conditionalLevels':conditional,'eventContracts':events,'triggerContracts':trigger_contracts,
    'triggerInstances':trigger_instances,'enums':enums,
    'mapRegistrations':[{**r,'rawExportPointer':f"/Exports/{r['exportIndex']-1}"} for r in table['records']],
    'nestedWorldReferences':{'records':unconfirmed_nested,
        'status':'stored sublevel World references, not demonstrated active registrations in MainLevel; not automatically added to baseline',
        'unknown':'runtime propagation of nested World streaming tables has not been established for this build'},
    'coverage':{'classPackagesScanned':len(inventory['sources']),'streamingCallsInClassPackages':call_counts,
        'mapsScanned':len(world_scan['maps']),'mapScriptStreamingCalls':sum(len(m['calls']) for m in world_scan['maps']),
        'serializedNativeLevelStreamingVolumes':sum(len(m['streamingVolumes']) for m in world_scan['maps']),
        'exactOffsetChecks':checks,'scanLimit':'explicit decoded function calls and serialized native volume identity, not arbitrary native behavior'},
    'unknowns':['No original runtime load completion/visibility trace; latent requests can fail or be superseded.',
        'Dynamic objects omit initial loaded/visible properties. Omission alone is not used to infer current visibility.',
        'AlwaysLoaded title level is resident, but title actors can be hidden by TitleOptions interface; not all level actors render simultaneously.',
        'Actor construction/BeginPlay scripts can alter visibility, collision, effects and transforms beyond package selection.',
        'Some CQ/Boss selector entries name packages absent from the 41 shipped /Game maps; use shippedPackageExists and do not invent replacement maps.',
        'Nested Lighting sublevel references are preserved separately; no invented recursive always-load behavior.',
        'No position-driven district streaming was found in the decoded call/volume scan; this does not prove absence of all native/custom behavior.']
}
write(OUT,manifest)
write(RESEARCH/'streaming-contract.json',manifest)
validation={'manifest':str(OUT),'sha256':sha(OUT),'baselineCount':len(baseline_names),
            'startupRequests':len(startup),'triggerInstances':len(trigger_instances),
            'startupLatentEdgesVerified':True,'functionOffsets':checks,'callCounts':call_counts,
            'missingCQLevelNames':[m['levelName'] for m in cq_mapping if not m['shippedPackageExists']],
            'sourceManifestSha256':{'mainLevelTable':sha(RESEARCH/'rea-audit/mainlevel-streaming-table.json'),
                                   'mapScan':sha(RESEARCH/'streaming-map-scan.json'),
                                   'callInventory':sha(RESEARCH/'streaming-call-inventory.json')}}
write(RESEARCH/'streaming-validation.json',validation)
print(json.dumps(validation,ensure_ascii=False))
