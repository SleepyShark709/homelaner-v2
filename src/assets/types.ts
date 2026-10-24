export interface AssetEntry {
  id: string;
  label: string;
  url: string;
  kind: 'character' | 'vehicle' | 'building' | 'prop';
  sourcePackage: string;
  notes?: string;
}

export interface AssetStats {
  meshes: number;
  triangles: number;
  bones: number;
  animations: string[];
  height: number;
  materials: number;
}
