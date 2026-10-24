# 原地形恢复与加载接口

恢复来自原 MainLevel 的高度像素，无手工高度或平面代替。源安装只读。结果 {"expectedLandscapeComponents": 144, "recoveredLandscapeComponents": 144, "restoredTextureCount": 66, "heightAtlasCount": 9, "weightmapCount": 57, "failedItems": 0, "fullResolutionVertices": 2322576, "renderVertices": 166464, "renderTriangles": 313632, "maxRenderHeightErrorMeters": 1.04296875, "neighborSeamsChecked": 264, "neighborSeamMaxU16Delta": 0, "subsectionBoundaryMaxU16Delta": 0, "elapsedSeconds": 13.27, "highQualityRenderVertices": 608400, "highQualityRenderTriangles": 1179648, "highQualityMaxHeightErrorMeters": 0.4375}。

## 接口

public/assets/world/terrain-manifest.json 的 assets/objects 可并入原世界加载。originUE=[0,0,0]，UE[x,y,z]转换为glTF[x,z,y]/100；每块GLB顶点是组件局部米坐标，objects.position为世界米坐标，rotation单位、scale=1。bounds是完整高度场边界，不仅是抽样LOD。

每块保留127×127 uint16小端高度，行=UE局部Y/世界Z，列=UE局部X/世界X。高度 worldY=heightBaseMeters+(uint16-heightOffset)*heightMultiplierMeters。水平坐标 worldX=position[0]+column*horizontalStepMeters[0]；worldZ=position[2]+row*horizontalStepMeters[1]。先用对象bounds查找块，再将XZ反变换到网格，按下述三角形采样。边界块可任取共享边，已逐点检查。

## 原像素与布局

高度atlas格式PF_B8G8R8A8，物理字节[B,G,R,A]，高度=R*256+G；线性数据，禁止sRGB转换、8位灰度降精度或PNG翻转。已用UModel单独导出的Texture2D_5 PNG逐RGBA像素交叉验证原ubulk读取。每个63-quad subsection存64个像素，两个subsection共128像素但只有127个唯一顶点：局部整数v的源像素=atlasOrigin+v+min(floor(v/63),1)。atlasOrigin=(HeightmapScaleBias.Z*textureWidth, .W*textureHeight)。内部重复边和相邻组件边全部独立验算。

## 轻量渲染与碰撞

默认glb是按4格抽样的LOD，额外保留63和126边界，所有顶点高度均来自原像素。每块lod.maxHeightErrorMeters给出对全部原网格顶点的实际最大误差；完整u16未降采样。不要把LOD渲染面误当原PhysX碰撞。原CollisionMipLevel=1也记录，但未重建原碰撞烹制数据。

如用完整高度场求高度，令gx,gz为网格浮点坐标，ix=floor(gx), iz=floor(gz), tx=gx-ix, tz=gz-iz。四角为h00,h10,h01,h11：tx+tz<=1 时 h=h00+(h10-h00)*tx+(h01-h00)*tz；否则 h=h11+(h01-h11)*(1-tx)+(h10-h11)*(1-tz)。这与本导出三角剖分一致，是明确的Web采样合同；并不宣称等于所有原PhysX细节。若用户接触的是渲染LOD，使用lod.sampleCoordinates界定单元而非单位格。

## 权重与材质边界

textures中PNG保存原RGBA通道；heightfields.weightmapLayers逐项列LayerInfo原引用、纹理URL、RGBA通道(0=R,1=G,2=B,3=A)。原weightmapScaleBias保留。以与高度同一subsection坐标在权重128²纹理中取像素，不按heightmap atlas bias取权重。LayerInfo原名字不等于完整着色配方，材质混合/纹理平铺/法线等仍需材质恢复。GLB没有编造的草地/灰色替代材质；materialStatus必须保留。

## 验证边界

所有恢复是源包静态资源重建，并非运行时游戏画面验证。完整证据、原map/ubulk SHA、纹理偏移、组件JSON pointers及接缝对照见terrain-recovery.json。

每个asset.highQualityUrl指向LOD2，asset.lods按[默认LOD4,高清LOD2]列出URL、顶点/三角形、SHA和误差。LOD2总608400顶点/1179648三角形，最大采样误差0.4375米；此数值应以manifest本次生成值为准。法线由完整高度差分计算，未还原原地形材质法线混合。
