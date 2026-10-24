import { Scene } from '@babylonjs/core/scene';
import { MeshBuilder } from '@babylonjs/core/Meshes/meshBuilder';
import type { Mesh } from '@babylonjs/core/Meshes/mesh';
import { StandardMaterial } from '@babylonjs/core/Materials/standardMaterial';
import { Color3 } from '@babylonjs/core/Maths/math.color';
import { Quaternion, Vector3 } from '@babylonjs/core/Maths/math.vector';
import type { Vec3 } from './collision';

export class Effects {
  private readonly red: StandardMaterial;
  private readonly gold: StandardMaterial;
  private readonly blue: StandardMaterial;
  private readonly beams: Mesh[];
  private readonly sparks: { mesh: Mesh; age: number; life: number; velocity: Vector3; size: number }[] = [];
  constructor(readonly scene: Scene) {
    const material = (name: string, color: string) => { const mat = new StandardMaterial(name, scene); mat.emissiveColor = Color3.FromHexString(color); mat.disableLighting = true; return mat; };
    this.red = material('heat-red', '#ff3122'); this.gold = material('impact-gold', '#ffd38a'); this.blue = material('fist-cyan', '#c5ffff');
    this.beams = [0, 1].map(index => { const mesh = MeshBuilder.CreateCylinder(`eye-beam-${index}`, { height: 1, diameter: 0.035, tessellation: 6 }, scene); mesh.material = this.red; mesh.isPickable = false; mesh.setEnabled(false); return mesh; });
  }
  heat(eyes: Vec3[] | null, end?: Vec3): void {
    this.beams.forEach((mesh, index) => {
      mesh.setEnabled(!!eyes && !!end);
      if (!eyes || !end) return;
      const start = Vector3.FromArray(eyes[index]), direction = Vector3.FromArray(end).subtract(start);
      const length = direction.length(); direction.normalize();
      mesh.position.copyFrom(start.add(direction.scale(length / 2)));
      mesh.scaling.y = length;
      const axis = Vector3.Cross(Vector3.Up(), direction);
      mesh.rotationQuaternion = axis.lengthSquared() < 1e-8 ? Quaternion.RotationAxis(Vector3.Right(), direction.y > 0 ? 0 : Math.PI) : Quaternion.RotationAxis(axis.normalize(), Math.acos(Math.max(-1, Math.min(1, direction.y))));
    });
  }
  projectile(): Mesh {
    const mesh = MeshBuilder.CreateSphere('fist-wave', { diameter: 0.8, segments: 6 }, this.scene);
    mesh.material = this.blue; mesh.isPickable = false; return mesh;
  }
  impact(point: Vec3, destroyed = false): void {
    const count = destroyed ? 8 : 2;
    for (let i = 0; i < count; i++) {
      if (this.sparks.length >= 64) this.sparks.shift()!.mesh.dispose();
      const size = destroyed ? 0.24 + i * 0.035 : 0.09;
      const mesh = MeshBuilder.CreateSphere('impact', { diameter: 1, segments: 4 }, this.scene);
      mesh.material = this.gold; mesh.isPickable = false; mesh.position.copyFromFloats(...point); mesh.scaling.setAll(size);
      const angle = i * 2.399;
      this.sparks.push({ mesh, age: 0, life: destroyed ? 0.85 : 0.18, size, velocity: new Vector3(Math.sin(angle) * (destroyed ? 7 : 2), 2 + i % 3, Math.cos(angle) * (destroyed ? 7 : 2)) });
    }
  }
  update(dt: number): void {
    for (let i = this.sparks.length - 1; i >= 0; i--) {
      const spark = this.sparks[i]; spark.age += dt;
      if (spark.age >= spark.life) { spark.mesh.dispose(); this.sparks.splice(i, 1); continue; }
      spark.velocity.y -= 5 * dt; spark.mesh.position.addInPlace(spark.velocity.scale(dt)); spark.mesh.scaling.setAll(spark.size * (1 - spark.age / spark.life));
    }
  }
  reset(): void { this.heat(null); this.sparks.forEach(spark => spark.mesh.dispose()); this.sparks.length = 0; }
  dispose(): void { this.reset(); this.beams.forEach(mesh => mesh.dispose()); this.red.dispose(); this.gold.dispose(); this.blue.dispose(); }
}
