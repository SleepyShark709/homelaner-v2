"""Enrich the static audit without changing any published game resources."""
import concurrent.futures
import importlib.util
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('audit_materials',HERE/'audit-materials.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
r=a.read(HERE/'material-coverage.json')
selected=[p for p in r['textureDependencies'] if p.split('/')[-1] in {
 'T_Contemporary_D','T_Contemporary_M','T_Contemporary_R','T_Contemporary_AO','T_Contemporary_N_Ydown','T_Contemporary_ID',
 'RoadMain_A','RoadMain_C','RoadMain_H','RoadMain_N','brick_01_d','brick_01_n','Brick_01_C','Brick_01_h',
 'T_Hair1_color','T_Hair_001_D','T_Hair_001_A','T_Hair_001_N_ydown','T_Male_Body_N_Ydown'}]
a.ensure_packages(selected)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 r['sampledTextureMetadata']=[item[0] for item in pool.map(a.decode_material,selected)]
r['statistics']['sampledTextureMetadataRecords']=len(r['sampledTextureMetadata'])
r['findings']=[
 {'id':'map-subset','status':'confirmed-static','summary':'Current Web uses a selected area, not the complete original city.',
  'source':'research/exports/city-decoded/MainLevel.json','sourceClassCounts':{'SplineMeshComponent':1952,'LandscapeComponent':144},
  'current':{'selectedSplineComponents':211,'selectedStaticObjects':41,'sourceMaps':['MainLevel','ResidentialArea1']},
  'implementation':'tools/asset-pipeline/export-city.py:15,256-260','limit':'Component totals are not all visible road segments; 211/1952 is component coverage, not area or visual-fidelity percentage.'},
 {'id':'unapplied-overrides','status':'confirmed-static','summary':'21 selected actors have 27 distinct override materials, recorded but not applied.',
  'source':'research/exports/city-decoded/ResidentialArea1.json','pointer':'/Exports/359/Data/2',
  'actor':'SM_MERGED_Apartment_AA_190','examples':{'0':'/Game/UrbanCity/Materials/Tileable/brick_01_Inst','1':'/Game/UrbanCity/Materials/Tileable/brick_02_TintA_Inst','10':'/Game/UrbanCity/Materials/Tileable/Window_Inst','15':'/Game/-HeroGame/Materials/MaterialInstance/MI_RoofTop'},
  'implementation':'tools/asset-pipeline/export-city.py:120-159; src/game/World.ts',
  'limit':'Original UE material slot numbers must not be equated with deduplicated glTF material indexes; original section-slot mapping is required.'},
 {'id':'white-plaster','status':'confirmed-static','summary':'The published white plaster has no base texture or normal map; original plaster also references normal and mildew maps, and some actor slots replace the default material.',
  'sourcePackage':'/Game/ModularStreetPack/Materials/PlasteredWall_MAT','sourcePointer':'/Exports/0/Data/5',
  'dependencies':['/Game/ModularStreetPack/Textures/T_Plastered_Wall_NRM','/Game/ModularStreetPack/Textures/T_Mildew_Map','/Game/ModularStreetPack/Textures/T_Mildew_GradientMap'],
  'limit':'Original Color default is white too. White is not by itself proof of a missing albedo; the proven losses are overrides, normal/mildew shading, and unverified lighting.'},
 {'id':'pbr-channels','status':'confirmed-static','summary':'Every current glTF omits normal, metallicRoughness, occlusion and emissive texture slots.',
  'source':'published entries in this document','implementation':'tools/asset-pipeline/publish_original.py; tools/asset-pipeline/export-city.py'},
 {'id':'road-shader','status':'confirmed-static','summary':'RoadMain_A_Inst has original BaseColor/Compact/Height/Normal and wetness parameters; Web keeps only BaseColor.',
  'sourcePackage':'/Game/Downtown/Materials/RoadMain_A_Inst','sourcePointers':['/Exports/0/Data/1','/Exports/0/Data/2','/Exports/0/Data/3'],
  'parent':'/Game/Downtown/Materials/-Pavement__Mat','parameterCollection':'/Game/Downtown/Materials/GlobalParameters/Environmental',
  'limit':'Compact RGB packing and shader math are not established by texture names. Environmental defaults are not proof of runtime values.'},
 {'id':'glass-multiple-models','status':'confirmed-static','summary':'Building glass, character lenses and car glass are separate shader families; current exporters replace each with arbitrary opaque constants.',
  'sources':[{'package':'/Game/ModularStreetPack/Materials/WindowGlass_Mat','pointer':'/Exports/0/Data/2','blend':'BLEND_Masked'},
             {'package':'/Game/Action_Male/Materials/M_GlassLens_master','pointer':'/Exports/0/Data/3','blend':'BLEND_Translucent'},
             {'package':'/Game/-WorkSpace/Hyodo/VehicleSystem/Vehicle/Sedan/Materials/M_Vehicle_Sedan_Inst_Glass','pointer':'/Exports/0/Data/2','roughness':0.10000000149011612}],
  'limit':'No serialized translucent override was found for Sedan glass. Do not apply a global transparent-glass fix.'},
 {'id':'character-shader','status':'confirmed-static','summary':'Body uses subsurface shading; clothing uses ID-region coloring and six texture channels; hair uses hue/value/opacity parameters. Current output reduces them to diffuse and tint.',
  'sources':[{'package':'/Game/Action_Male/Materials/M_Body_master','pointer':'/Exports/0/Data/3'},
             {'package':'/Game/Action_Male/Materials/MI_Clothes_Contemporary_AllBlack','pointer':'/Exports/0/Data/3'},
             {'package':'/Game/Action_Male/Materials/MI_Hair_Black','pointer':'/Exports/0/Data/2'}],
  'limit':'Hair instance TextureParameterValues and CachedReferencedTextures disagree between Hair1 and Hair_001 families; final compiled binding needs additional verification.'},
 {'id':'vehicle-original-parameters','status':'confirmed-static','summary':'UModel empty-parameters messages do not mean the original material has no parameters. UAssetAPI recovers the scalar/vector material parameters.',
  'sourcePackage':'/Game/-WorkSpace/Hyodo/VehicleSystem/Vehicle/Sedan/Materials/M_Vehicle_Sedan','pointer':'/Exports/0/Data/5',
  'originalDefaults':{'Roughness':0.5,'Metallic':0,'Base color':[0,0.6800000071525574,0.9399999976158142,1]},
  'currentDefaults':{'roughnessFactor':0.32,'metallicFactor':0.45,'baseColorFactor':[0.11,0.27,0.36,1]},
  'limit':'The inspected sedan material family has no imported Texture2D; missing texture is not the supported explanation for this asset.'},
 {'id':'lighting-not-recovered','status':'confirmed-implementation','summary':'Current fog, sky, sunlight and shadow constants were chosen by Web implementation; source Lighting map/post-process/reflection/lightmaps were not used.',
  'implementation':'src/game/Game.ts:48-59','sourceCandidate':'UNDEFEATED/Content/-HeroGame/Maps/SubLevel/Lighting.umap','limit':'Original lighting values are not recovered in this audit.'}
]
r['reconstructionDependencies']=[
 {'stage':'world-closure','required':['Resolve actual MainLevel streaming levels and scenario activation, not every test map in Pak.','Extract all mesh/landscape/spline/foliage/decal instances, transforms, LOD and visibility from active maps.','Traverse mesh, material, blueprint dynamic-material and texture dependencies.'],'inventory':'pakGameMapPaths (41 packages), mapReferencedResourceDependencies (330 packages from four inspected maps); neither is the complete active-world closure.'},
 {'stage':'material-slots','required':['Retain original UE material slot and LOD section mapping before material deduplication.','Apply component OverrideMaterials and blueprint-created material overrides per instance.','Resolve parent chain and enabled BasePropertyOverrides, static switches, cached defaults and runtime updates.'],'inventory':'mapMaterialOverrides contains exact raw JSON pointers; sourceMaterialDependencyClosure contains 129 static-decoded packages.'},
 {'stage':'textures-and-shaders','required':['Export pixels/mips for textureDependencies (164), plus dependencies discovered from remaining maps.','Preserve sRGB, compression, normal Y convention, sampler, UV scale and channels.','Recover Compact channel packing before packing glTF ORM; do not assume ORM from filenames.','Reconstruct body SSS, region ID masks, layered pavement/wetness, hair opacity and correct glass family.','Verify compiled shader bindings where cached references differ from editable parameter metadata.'],'inventory':'sampledTextureMetadata contains raw texture metadata, source hashes and pointers; source material Extras remain opaque compiled data.'},
 {'stage':'geometry-attributes','required':['Keep tangent, additional UVs and vertex colors when present; current spline bake retains only POSITION/NORMAL/TEXCOORD_0.','Preserve spline deformation plus per-component materials.','Restore landscape height/weight maps and foliage/decal geometry separately.']},
 {'stage':'lighting-and-validation','required':['Decode active lighting/sky/postprocess/reflection and baked-light data and record approximation decisions.','Compare the same original/Web location, view, time and weather with captures.','Use REA native sessions only when available; keep independent tool outputs explicitly separate from REA Evidence.'],'limit':'No original runtime screenshot comparison performed by this audit.'}
]
r['unresolved']=['Whole active-city dependency closure','Runtime-created/modified materials','Compiled shader graphs and texture channel packing','Effective Hair1 versus Hair_001 compiled binding','Original lighting and environment state','Original-runtime matched-camera visual comparison']
r['provenance']['auditScripts']={str(p.relative_to(a.ROOT)):a.sha(p) for p in [HERE/'audit-materials.py',Path(__file__)]}
a.write(HERE/'material-coverage.json',r)
print('Enriched audit; texture metadata:',len(r['sampledTextureMetadata']))
