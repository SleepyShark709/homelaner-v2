"""Reproduce this bounded export without launching the game or a viewer.

Requires the local repak tool and the portable official UEViewer binary.
Exports only named asset groups, not the complete game.
"""
import argparse
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--pak', default=r'E:\SteamLibrary\steamapps\common\UNDEFEATED\UNDEFEATED\Content\Paks\UNDEFEATED-WindowsNoEditor.pak')
parser.add_argument('--repak', default=str(ROOT / 'tools/asset-pipeline/bin/repak.exe'))
args = parser.parse_args()
unpacked = ROOT / 'research/exports/unpacked'
prefixes = ['Action_Male/', '-HeroGame/Player/Animations/', '-HeroGame/Mesh/Buildings/', '-WorkSpace/Hyodo/VehicleSystem/Vehicle/Sedan/', 'ModularStreetPack/Materials/', 'ModularStreetPack/Textures/']
command = [args.repak, 'unpack', args.pak, '-o', str(unpacked)]
for prefix in prefixes:
    command += ['-i', 'UNDEFEATED/Content/' + prefix]
subprocess.run(command, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
exe = ROOT / 'tools/asset-pipeline/umodel.exe'
jobs = [
    ('hero', 'SK_Male_Contemporary_standalone'),
    ('accessories', 'SK_Hair_001_pompadour'),
    ('accessories', 'SK_Sunglasses'),
    ('building', 'SM_MERGED_Apartment_A'),
    ('vehicle', 'Sedan_SkelMesh'),
    ('animations', 'Hero_Idle'),
    ('animations', 'Hero_IdleFlying'),
    ('animations', 'Hero_FlyFastSprint'),
    ('animations', 'A_ThirdPersonRun'),
]
for category, name in jobs:
    command = [str(exe), '-export', '-game=ue4.27', '-psk' if category == 'animations' else '-gltf', '-png', '-path=' + (unpacked / 'UNDEFEATED/Content').as_posix(), '-out=' + (ROOT / 'research/exports' / category).as_posix(), name]
    result = subprocess.run(command, cwd=exe.parent, capture_output=True, timeout=90, creationflags=subprocess.CREATE_NO_WINDOW)
    (ROOT / ('research/evidence/asset-export-' + name + '.log')).write_bytes(result.stdout + result.stderr)
    result.check_returncode()
    print(name, 'exported')
