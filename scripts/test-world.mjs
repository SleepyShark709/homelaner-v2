import assert from 'node:assert/strict';
import { resolveMaterialPackage, explicitlyHidden, sourceObjectCount } from '../src/world/types.ts';
import { canonicalMaterialSource } from '../src/world/material-identity.ts';

const asset = { id: 'original-section-fixture', url: '/fixture.gltf',
  sourceMaterialSlots: [
    { slotIndex: 0, material: { package: '/Game/Mat/Wall' } },
    { slotIndex: 1, material: { package: '/Game/Mat/Window' } },
    { slotIndex: 2, material: { package: '/Game/Mat/Wall' } },
  ], gltfMaterials: [
    { materialIndex: 0, name: 'Window', sourceSlotCandidates: [1] },
    { materialIndex: 1, name: 'Wall', sourceSlotCandidates: [0, 2] },
  ] };
// Native UE slot 1 is not glTF material index 1: conversion must retain the map.
assert.deepEqual(resolveMaterialPackage(asset, 0, [{slotIndex: 1, material:{package:'/Game/Mat/Glass'}}]), {package:'/Game/Mat/Glass', ambiguous:false});
assert.deepEqual(resolveMaterialPackage(asset, 0, [{slotIndex: 1, material:null}]), {package:'/Game/Mat/Window', ambiguous:false});
assert.deepEqual(resolveMaterialPackage(asset, 1), {package:'/Game/Mat/Wall', ambiguous:false});
// Different overrides on merged/ambiguous original slots may not be guessed.
assert.deepEqual(resolveMaterialPackage(asset, 1, [{slotIndex: 2, material:{package:'/Game/Mat/Brick'}}]), {package:null, ambiguous:true});
assert.deepEqual(resolveMaterialPackage(asset, 1, [0,2].map(slotIndex=>({slotIndex,material:{package:'/Game/Map#export:18'}}))), {package:'/Game/Map#export:18', ambiguous:false});
assert.deepEqual(resolveMaterialPackage(asset, 88), {package:null, ambiguous:false});
assert.equal(explicitlyHidden({visibilityProperties:{bVisible:false}}), true);
assert.equal(explicitlyHidden({visibilityProperties:{actorHidden:true}}), true);
assert.equal(explicitlyHidden({visibilityProperties:{}}), false);
assert.equal(sourceObjectCount({sourceComponents:[{id:'Spline1'},{id:'Spline2'}]}), 2);
assert.equal(sourceObjectCount({}), 1);
const parent = {sourcePackage:'/Game/Parent',baseMaterial:'/Game/Base',channels:{},factors:{roughness:.5}};
const emptyMID = {...parent,sourcePackage:'/Game/Map#export:1',parent:parent.sourcePackage,
  embeddedInstance:{className:'MaterialInstanceDynamic',sourceParameters:[],remainingProperties:[{name:'CachedReferencedTextures'}]}};
const manifest = {materials:{[parent.sourcePackage]:parent,[emptyMID.sourcePackage]:emptyMID}};
assert.equal(canonicalMaterialSource(emptyMID.sourcePackage,manifest), parent.sourcePackage);
// Retain identity when a MID has a real override or an unhandled saved property.
for (const changed of [
  {...emptyMID,factors:{roughness:.7}},
  {...emptyMID,embeddedInstance:{...emptyMID.embeddedInstance,sourceParameters:[{name:'Emissive'}]}},
  {...emptyMID,embeddedInstance:{...emptyMID.embeddedInstance,remainingProperties:[{name:'UnknownOverride'}]}},
]) {
  assert.equal(canonicalMaterialSource(emptyMID.sourcePackage,{materials:{...manifest.materials,[emptyMID.sourcePackage]:changed}}),emptyMID.sourcePackage);
}
console.log('World material-slot provenance, explicit visibility and source-count checks passed.');
