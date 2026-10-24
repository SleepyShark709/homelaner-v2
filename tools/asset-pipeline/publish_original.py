"""Publish bounded UModel exports. Original geometry is unchanged; UE shaders are approximated.
Run after exporting into research/exports/{hero,accessories,building,vehicle}.
"""
import hashlib
import json
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
EXPORTS = ROOT / 'research/exports'
PUBLIC = ROOT / 'public/assets/original'
ITEMS = [
    ('hero', '原版主角', 'hero', 'SK_Male_Contemporary_standalone', 'character'),
    ('hair', '原版主角头发', 'accessories', 'SK_Hair_001_pompadour', 'prop'),
    ('sunglasses', '墨镜附件', 'accessories', 'SK_Sunglasses', 'prop'),
    ('building', '原版公寓楼', 'building', 'SM_MERGED_Apartment_A', 'building'),
    ('vehicle', '原版车辆样本', 'vehicle', 'Sedan_SkelMesh', 'vehicle'),
]

def color_parameter(props):
    m = re.search(r'Name=Color\s*\}.*?ParameterValue = \{ R=([\d.e-]+), G=([\d.e-]+), B=([\d.e-]+), A=([\d.e-]+)', props, re.S)
    return list(map(float, m.groups())) if m else None

def build():
    catalog = []
    evidence = []
    for id, label, category, name, kind in ITEMS:
        if len(sys.argv) > 1 and id not in sys.argv[1:]: continue
        srcroot = EXPORTS / category
        source = next(srcroot.rglob(name + '.gltf'))
        doc = json.loads(source.read_text())
        dest = PUBLIC / id
        dest.mkdir(parents=True, exist_ok=True)
        for buffer in doc['buffers']:
            shutil.copy2(source.parent / buffer['uri'], dest / buffer['uri'])
        texfiles = {p.stem.lower(): p for p in srcroot.rglob('*.png')}
        matfiles = {p.stem: p for p in srcroot.rglob('*.mat')}
        propfiles = {p.name.removesuffix('.props.txt'): p for p in srcroot.rglob('*.props.txt')}
        image_cache = {}
        mapping = []
        def texture(name):
            if name not in image_cache:
                file = texfiles[name.lower()]
                (dest / 'textures').mkdir(exist_ok=True)
                shutil.copy2(file, dest / 'textures' / file.name)
                index = len(doc.setdefault('images', []))
                doc['images'].append({'uri': 'textures/' + file.name})
                doc.setdefault('textures', []).append({'source': index})
                image_cache[name] = index
            return {'index': image_cache[name]}
        for mat in doc['materials']:
            n = mat['name']
            props = propfiles[n].read_text() if n in propfiles else ''
            pbr = mat['pbrMetallicRoughness'] = {'baseColorFactor': [0.65, 0.65, 0.65, 1], 'metallicFactor': 0, 'roughnessFactor': 0.75}
            diffuse = None
            if n in matfiles:
                match = re.search(r'^Diffuse=(.+)$', matfiles[n].read_text(), re.M)
                if match:
                    candidate = match[1].strip()
                    if not any(x in candidate.lower() for x in ['height', 'alpha', 'mask', 'metalic', 'gradient', 'windowgrime']):
                        diffuse = candidate
            if n == 'M_ShadowTrim': pbr['baseColorFactor'] = [0.006, 0.006, 0.006, 1]
            if n == 'MI_Body_asian': pbr['baseColorFactor'] = [0.743119] * 3 + [1]
            if n == 'MI_Clothes_Contemporary_AllBlack': pbr['baseColorFactor'] = [0.045] * 3 + [1]
            if n == 'MI_Hair_005a':
                diffuse = 'T_Hair_005_D'
                pbr['baseColorFactor'] = [0.2] * 3 + [1]
            if n == 'MI_Hair_Black':
                diffuse = 'T_Hair1_color'
                pbr['baseColorFactor'] = [0.025] * 3 + [1]
            if 'Red_Brick' in n: diffuse = 'T_Red_Brick'
            if 'PolishedConcrete' in n: diffuse = 'T_Polished_Concrete'
            if 'Generic_Color' in n: diffuse = None
            if c := color_parameter(props): pbr['baseColorFactor'] = c
            if 'Glass' in n or 'Sunglasses' in n or 'GlassLens' in n:
                pbr.update(baseColorFactor=[0.025, 0.04, 0.05, 1], metallicFactor=0.2, roughnessFactor=0.18)
            if category == 'vehicle':
                # Browser QA: this source geometry is open-top. Explicitly opaque
                # materials document that a roof is not being hidden by blending.
                mat['alphaMode'] = 'OPAQUE'
                if 'Tires' in n: pbr['baseColorFactor'] = [0.012] * 3 + [1]
                elif 'Plastic' in n: pbr['baseColorFactor'] = [0.025] * 3 + [1]
                elif 'TailLights' in n: pbr['baseColorFactor'] = [0.5, 0.015, 0.01, 1]
                elif 'Headlights' in n: pbr['baseColorFactor'] = [0.8, 0.85, 0.8, 1]
                elif 'Wheels' in n: pbr.update(baseColorFactor=[0.4]*3+[1], metallicFactor=0.8, roughnessFactor=0.3)
                elif n == 'M_Vehicle_Sedan': pbr.update(baseColorFactor=[0.11, 0.27, 0.36, 1], metallicFactor=0.45, roughnessFactor=0.32)
            if diffuse and diffuse.lower() in texfiles:
                pbr['baseColorTexture'] = texture(diffuse)
            mapping.append({'material': n, 'baseColorTexture': diffuse, 'baseColorFactor': pbr['baseColorFactor']})
        doc.setdefault('asset', {})['extras'] = {'source': source.relative_to(EXPORTS).as_posix(), 'conversion': 'UModel geometry, simplified PBR materials; original UE shaders not reproduced'}
        if category == 'vehicle':
            doc['asset']['extras']['geometryLimitation'] = 'This Sedan_SkelMesh sample has open-top cabin geometry. Closed-roof completeness and any separate blueprint attachment are unverified.'
        output = dest / (id + '.gltf')
        output.write_text(json.dumps(doc, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        notes = '从本机原版资产导出的真实网格和蒙皮；已关联颜色贴图，材质为简化PBR，未重建UE法线、分层遮罩、皮肤散射与折射效果。'
        if kind == 'prop': notes += ' 附件为独立局部坐标模型，尚未按原蓝图挂接主角头骨。'
        if kind == 'building': notes += ' 窗户当前偏白，原玻璃和窗面材质仍需还原。'
        if kind == 'vehicle': notes = '原版车辆网格与6根骨骼。此网格没有封闭顶棚，尚未确认原蓝图是否另装顶棚；车漆、灯光与玻璃使用简化材质。'
        if category == 'vehicle': notes = '原版 Sedan_SkelMesh 车辆样本，保留6根骨骼；原导出网格座舱开放，材质全部不透明，不应视作完整封闭车顶轿车；车漆与玻璃使用简化PBR。'
        catalog.append({'id': id, 'label': label, 'url': '/assets/original/' + id + '/' + id + '.gltf', 'kind': kind, 'sourcePackage': '/Game/' + source.relative_to(srcroot).with_suffix('').as_posix(), 'notes': notes})
        primitives = doc['meshes'][0]['primitives']
        evidence.append({'id': id, 'file': str(output), 'sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'joints': sum(len(x['joints']) for x in doc.get('skins', [])), 'triangles': sum(doc['accessors'][p['indices']]['count']//3 for p in primitives), 'materials': mapping})
    for target, records in [(PUBLIC / 'catalog.json', catalog), (ROOT / 'research/evidence/asset-export-published.json', evidence)]:
        if len(sys.argv) > 1 and target.exists():
            old = json.loads(target.read_text(encoding='utf-8'))
            ids = {r['id'] for r in records}
            records = [r for r in old if r['id'] not in ids] + records
        target.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps([{'id': x['id'], 'file': x['file'], 'joints': x['joints'], 'triangles': x['triangles']} for x in evidence], indent=2))

if __name__ == '__main__': build()
