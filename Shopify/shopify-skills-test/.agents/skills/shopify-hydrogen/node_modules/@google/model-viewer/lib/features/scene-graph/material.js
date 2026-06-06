/* @license
 * Copyright 2020 Google LLC. All Rights Reserved.
 * Licensed under the Apache License, Version 2.0 (the 'License');
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an 'AS IS' BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
var _a, _b;
import { Color, DoubleSide, FrontSide, Vector2 } from 'three';
import { PBRMetallicRoughness } from './pbr-metallic-roughness.js';
import { TextureInfo, TextureUsage } from './texture-info.js';
import { $correlatedObjects, $onUpdate, ThreeDOMElement } from './three-dom-element.js';
const $pbrMetallicRoughness = Symbol('pbrMetallicRoughness');
const $normalTexture = Symbol('normalTexture');
const $occlusionTexture = Symbol('occlusionTexture');
const $emissiveTexture = Symbol('emissiveTexture');
const $backingThreeMaterial = Symbol('backingThreeMaterial');
const $applyAlphaCutoff = Symbol('applyAlphaCutoff');
const $getAlphaMode = Symbol('getAlphaMode');
export const $lazyLoadGLTFInfo = Symbol('lazyLoadGLTFInfo');
const $initialize = Symbol('initialize');
export const $getLoadedMaterial = Symbol('getLoadedMaterial');
export const $ensureMaterialIsLoaded = Symbol('ensureMaterialIsLoaded');
export const $gltfIndex = Symbol('gltfIndex');
export const $setActive = Symbol('setActive');
export const $variantIndices = Symbol('variantIndices');
const $isActive = Symbol('isActive');
const $modelVariants = Symbol('modelVariants');
const $name = Symbol('name');
const $pbrTextures = Symbol('pbrTextures');
/**
 * Material facade implementation for Three.js materials
 */
export class Material extends ThreeDOMElement {
    get [(_a = $variantIndices, _b = $pbrTextures, $backingThreeMaterial)]() {
        return this[$correlatedObjects]
            .values()
            .next()
            .value;
    }
    constructor(onUpdate, gltfIndex, isActive, modelVariants, correlatedMaterials, name, lazyLoadInfo = undefined) {
        super(onUpdate, correlatedMaterials);
        this[_a] = new Set();
        this[_b] = new Map();
        this[$gltfIndex] = gltfIndex;
        this[$isActive] = isActive;
        this[$modelVariants] = modelVariants;
        this[$name] = name;
        if (lazyLoadInfo == null) {
            this[$initialize]();
        }
        else {
            this[$lazyLoadGLTFInfo] = lazyLoadInfo;
        }
    }
    [$initialize]() {
        const onUpdate = this[$onUpdate];
        const correlatedMaterials = this[$correlatedObjects];
        this[$pbrMetallicRoughness] =
            new PBRMetallicRoughness(onUpdate, correlatedMaterials);
        const { normalMap, aoMap, emissiveMap } = correlatedMaterials.values().next().value;
        this[$normalTexture] = new TextureInfo(onUpdate, TextureUsage.Normal, normalMap, correlatedMaterials);
        this[$occlusionTexture] = new TextureInfo(onUpdate, TextureUsage.Occlusion, aoMap, correlatedMaterials);
        this[$emissiveTexture] = new TextureInfo(onUpdate, TextureUsage.Emissive, emissiveMap, correlatedMaterials);
        const createTextureInfo = (usage) => {
            this[$pbrTextures].set(usage, new TextureInfo(onUpdate, usage, null, correlatedMaterials));
        };
        createTextureInfo(TextureUsage.Clearcoat);
        createTextureInfo(TextureUsage.ClearcoatRoughness);
        createTextureInfo(TextureUsage.ClearcoatNormal);
        createTextureInfo(TextureUsage.SheenColor);
        createTextureInfo(TextureUsage.SheenRoughness);
        createTextureInfo(TextureUsage.Transmission);
        createTextureInfo(TextureUsage.Thickness);
        createTextureInfo(TextureUsage.Specular);
        createTextureInfo(TextureUsage.SpecularColor);
        createTextureInfo(TextureUsage.Iridescence);
        createTextureInfo(TextureUsage.IridescenceThickness);
        createTextureInfo(TextureUsage.Anisotropy);
    }
    async [$getLoadedMaterial]() {
        if (this[$lazyLoadGLTFInfo] != null) {
            const material = await this[$lazyLoadGLTFInfo].doLazyLoad();
            this[$initialize]();
            // Releases lazy load info.
            this[$lazyLoadGLTFInfo] = undefined;
            // Redefines the method as a noop method.
            this.ensureLoaded = async () => { };
            return material;
        }
        return null;
    }
    colorFromRgb(rgb) {
        const color = new Color();
        if (rgb instanceof Array) {
            color.fromArray(rgb);
        }
        else {
            color.set(rgb);
        }
        return color;
    }
    [$ensureMaterialIsLoaded]() {
        if (this[$lazyLoadGLTFInfo] == null) {
            return;
        }
        throw new Error(`Material "${this.name}" has not been loaded, call 'await
    myMaterial.ensureLoaded()' before using an unloaded material.`);
    }
    async ensureLoaded() {
        await this[$getLoadedMaterial]();
    }
    get isLoaded() {
        return this[$lazyLoadGLTFInfo] == null;
    }
    get isActive() {
        return this[$isActive];
    }
    [$setActive](isActive) {
        this[$isActive] = isActive;
    }
    get name() {
        return this[$name] || '';
    }
    set name(name) {
        this[$name] = name;
        if (this[$correlatedObjects] != null) {
            for (const threeMaterial of this[$correlatedObjects]) {
                threeMaterial.name = name;
            }
        }
    }
    get pbrMetallicRoughness() {
        this[$ensureMaterialIsLoaded]();
        return this[$pbrMetallicRoughness];
    }
    get normalTexture() {
        this[$ensureMaterialIsLoaded]();
        return this[$normalTexture];
    }
    get occlusionTexture() {
        this[$ensureMaterialIsLoaded]();
        return this[$occlusionTexture];
    }
    get emissiveTexture() {
        this[$ensureMaterialIsLoaded]();
        return this[$emissiveTexture];
    }
    get emissiveFactor() {
        this[$ensureMaterialIsLoaded]();
        return this[$backingThreeMaterial].emissive.toArray();
    }
    get index() {
        return this[$gltfIndex];
    }
    hasVariant(name) {
        const variantData = this[$modelVariants].get(name);
        return variantData != null && this[$variantIndices].has(variantData.index);
    }
    setEmissiveFactor(rgb) {
        this[$ensureMaterialIsLoaded]();
        const color = this.colorFromRgb(rgb);
        for (const material of this[$correlatedObjects]) {
            material.emissive.set(color);
        }
        this[$onUpdate]();
    }
    [$getAlphaMode]() {
        // Follows implementation of GLTFExporter from three.js
        if (this[$backingThreeMaterial].transparent) {
            return 'BLEND';
        }
        else {
            if (this[$backingThreeMaterial].alphaTest > 0.0) {
                return 'MASK';
            }
        }
        return 'OPAQUE';
    }
    [$applyAlphaCutoff]() {
        this[$ensureMaterialIsLoaded]();
        for (const material of this[$correlatedObjects]) {
            if (this[$getAlphaMode]() === 'MASK') {
                if (material.alphaTest == undefined) {
                    material.alphaTest = 0.5;
                }
            }
            else {
                material.alphaTest = undefined;
            }
            material.needsUpdate = true;
        }
    }
    setAlphaCutoff(cutoff) {
        this[$ensureMaterialIsLoaded]();
        for (const material of this[$correlatedObjects]) {
            material.alphaTest = cutoff;
            material.needsUpdate = true;
        }
        // Set AlphaCutoff to undefined if AlphaMode is not MASK.
        this[$applyAlphaCutoff]();
        this[$onUpdate]();
    }
    getAlphaCutoff() {
        this[$ensureMaterialIsLoaded]();
        return this[$backingThreeMaterial].alphaTest;
    }
    setDoubleSided(doubleSided) {
        this[$ensureMaterialIsLoaded]();
        for (const material of this[$correlatedObjects]) {
            // When double-sided is disabled gltf spec dictates that Back-Face culling
            // must be disabled, in three.js parlance that would mean FrontSide
            // rendering only.
            // https://github.com/KhronosGroup/glTF/tree/master/specification/2.0#double-sided
            material.side = doubleSided ? DoubleSide : FrontSide;
            material.needsUpdate = true;
        }
        this[$onUpdate]();
    }
    getDoubleSided() {
        this[$ensureMaterialIsLoaded]();
        return this[$backingThreeMaterial].side == DoubleSide;
    }
    setAlphaMode(alphaMode) {
        this[$ensureMaterialIsLoaded]();
        const enableTransparency = (material, enabled) => {
            material.transparent = enabled;
            material.depthWrite = !enabled;
        };
        for (const material of this[$correlatedObjects]) {
            enableTransparency(material, alphaMode === 'BLEND');
            if (alphaMode === 'MASK') {
                material.alphaTest = 0.5;
            }
            else {
                material.alphaTest = undefined;
            }
            material.needsUpdate = true;
        }
        this[$onUpdate]();
    }
    getAlphaMode() {
        this[$ensureMaterialIsLoaded]();
        return this[$getAlphaMode]();
    }
    /**
     * PBR Next properties.
     */
    // KHR_materials_emissive_strength
    get emissiveStrength() {
        this[$ensureMaterialIsLoaded]();
        return this[$backingThreeMaterial].emissiveIntensity;
    }
    setEmissiveStrength(emissiveStrength) {
        this[$ensureMaterialIsLoaded]();
        for (const material of this[$correlatedObjects]) {
            material.emissiveIntensity = emissiveStrength;
        }
        this[$onUpdate]();
    }
    // KHR_materials_clearcoat
    get clearcoatFactor() {
        this[$ensureMaterialIsLoaded]();
        return this[$backingThreeMaterial].clearcoat;
    }
    get clearcoatRoughnessFactor() {
        this[$ensureMaterialIsLoaded]();
        return this[$backingThreeMaterial].clearcoatRoughness;
    }
    get clearcoatTexture() {
        this[$ensureMaterialIsLoaded]();
        return this[$pbrTextures].get(TextureUsage.Clearcoat);
    }
    get clearcoatRoughnessTexture() {
        this[$ensureMaterialIsLoaded]();
        return this[$pbrTextures].get(TextureUsage.ClearcoatRoughness);
    }
    get clearcoatNormalTexture() {
        this[$ensureMaterialIsLoaded]();
        return this[$pbrTextures].get(TextureUsage.ClearcoatNormal);
    }
    get clearcoatNormalScale() {
        this[$ensureMaterialIsLoaded]();
        return this[$backingThreeMaterial].clearcoatNormalScale.x;
    }
    setClearcoatFactor(clearcoatFactor) {
        this[$ensureMaterialIsLoaded]();
        for (const material of this[$correlatedObjects]) {
            material.clearcoat = clearcoatFactor;
        }
        this[$onUpdate]();
    }
    setClearcoatRoughnessFactor(clearcoatRoughnessFactor) {
        this[$ensureMaterialIsLoaded]();
        for (const material of this[$correlatedObjects]) {
            material.clearcoatRoughness = clearcoatRoughnessFactor;
        }
        this[$onUpdate]();
    }
    setClearcoatNormalScale(clearcoatNormalScale) {
        this[$ensureMaterialIsLoaded]();
        for (const material of this[$correlatedObjects]) {
            material.clearcoatNormalScale =
                new Vector2(clearcoatNormalScale, clearcoatNormalScale);
        }
        this[$onUpdate]();
    }
    // KHR_materials_ior
    get ior() {
        this[$ensureMaterialIsLoaded]();
        return this[$backingThreeMaterial].ior;
    }
    setIor(ior) {
        this[$ensureMaterialIsLoaded]();
        for (const material of this[$correlatedObjects]) {
            material.ior = ior;
        }
        this[$onUpdate]();
    }
    // KHR_materials_sheen
    get sheenColorFactor() {
        this[$ensureMaterialIsLoaded]();
        return this[$backingThreeMaterial].sheenColor.toArray();
    }
    get sheenColorTexture() {
        this[$ensureMaterialIsLoaded]();
        return this[$pbrTextures].get(TextureUsage.SheenColor);
    }
    get sheenRoughnessFactor() {
        this[$ensureMaterialIsLoaded]();
        return this[$backingThreeMaterial].sheenRoughness;
    }
    get sheenRoughnessTexture() {
        this[$ensureMaterialIsLoaded]();
        return this[$pbrTextures].get(TextureUsage.SheenRoughness);
    }
    setSheenColorFactor(rgb) {
        this[$ensureMaterialIsLoaded]();
        const color = this.colorFromRgb(rgb);
        for (const material of this[$correlatedObjects]) {
            material.sheenColor.set(color);
            // Three.js GLTFExporter checks for internal sheen value.
            material.sheen = 1;
        }
        this[$onUpdate]();
    }
    setSheenRoughnessFactor(roughness) {
        this[$ensureMaterialIsLoaded]();
        for (const material of this[$correlatedObjects]) {
            material.sheenRoughness = roughness;
            // Three.js GLTFExporter checks for internal sheen value.
            material.sheen = 1;
        }
        this[$onUpdate]();
    }
    // KHR_materials_transmission
    get transmissionFactor() {
        this[$ensureMaterialIsLoaded]();
        return this[$backingThreeMaterial].transmission;
    }
    get transmissionTexture() {
        this[$ensureMaterialIsLoaded]();
        return this[$pbrTextures].get(TextureUsage.Transmission);
    }
    setTransmissionFactor(transmission) {
        this[$ensureMaterialIsLoaded]();
        for (const material of this[$correlatedObjects]) {
            material.transmission = transmission;
        }
        this[$onUpdate]();
    }
    // KHR_materials_volume
    get thicknessFactor() {
        this[$ensureMaterialIsLoaded]();
        return this[$backingThreeMaterial].thickness;
    }
    get thicknessTexture() {
        this[$ensureMaterialIsLoaded]();
        return this[$pbrTextures].get(TextureUsage.Thickness);
    }
    get attenuationDistance() {
        this[$ensureMaterialIsLoaded]();
        return this[$backingThreeMaterial].attenuationDistance;
    }
    get attenuationColor() {
        this[$ensureMaterialIsLoaded]();
        return this[$backingThreeMaterial].attenuationColor.toArray();
    }
    setThicknessFactor(thickness) {
        this[$ensureMaterialIsLoaded]();
        for (const material of this[$correlatedObjects]) {
            material.thickness = thickness;
        }
        this[$onUpdate]();
    }
    setAttenuationDistance(attenuationDistance) {
        this[$ensureMaterialIsLoaded]();
        for (const material of this[$correlatedObjects]) {
            material.attenuationDistance = attenuationDistance;
        }
        this[$onUpdate]();
    }
    setAttenuationColor(rgb) {
        this[$ensureMaterialIsLoaded]();
        const color = this.colorFromRgb(rgb);
        for (const material of this[$correlatedObjects]) {
            material.attenuationColor.set(color);
        }
        this[$onUpdate]();
    }
    // KHR_materials_specular
    get specularFactor() {
        this[$ensureMaterialIsLoaded]();
        return this[$backingThreeMaterial].specularIntensity;
    }
    get specularTexture() {
        this[$ensureMaterialIsLoaded]();
        return this[$pbrTextures].get(TextureUsage.Specular);
    }
    get specularColorFactor() {
        this[$ensureMaterialIsLoaded]();
        return this[$backingThreeMaterial].specularColor.toArray();
    }
    get specularColorTexture() {
        this[$ensureMaterialIsLoaded]();
        return this[$pbrTextures].get(TextureUsage.SheenColor);
    }
    setSpecularFactor(specularFactor) {
        this[$ensureMaterialIsLoaded]();
        for (const material of this[$correlatedObjects]) {
            material.specularIntensity = specularFactor;
        }
        this[$onUpdate]();
    }
    setSpecularColorFactor(rgb) {
        this[$ensureMaterialIsLoaded]();
        const color = this.colorFromRgb(rgb);
        for (const material of this[$correlatedObjects]) {
            material.specularColor.set(color);
        }
        this[$onUpdate]();
    }
    // KHR_materials_iridescence
    get iridescenceFactor() {
        this[$ensureMaterialIsLoaded]();
        return this[$backingThreeMaterial].iridescence;
    }
    get iridescenceTexture() {
        this[$ensureMaterialIsLoaded]();
        return this[$pbrTextures].get(TextureUsage.Iridescence);
    }
    get iridescenceIor() {
        this[$ensureMaterialIsLoaded]();
        return this[$backingThreeMaterial].iridescenceIOR;
    }
    get iridescenceThicknessMinimum() {
        this[$ensureMaterialIsLoaded]();
        return this[$backingThreeMaterial].iridescenceThicknessRange[0];
    }
    get iridescenceThicknessMaximum() {
        this[$ensureMaterialIsLoaded]();
        return this[$backingThreeMaterial].iridescenceThicknessRange[1];
    }
    get iridescenceThicknessTexture() {
        this[$ensureMaterialIsLoaded]();
        return this[$pbrTextures].get(TextureUsage.IridescenceThickness);
    }
    setIridescenceFactor(iridescence) {
        this[$ensureMaterialIsLoaded]();
        for (const material of this[$correlatedObjects]) {
            material.iridescence = iridescence;
        }
        this[$onUpdate]();
    }
    setIridescenceIor(ior) {
        this[$ensureMaterialIsLoaded]();
        for (const material of this[$correlatedObjects]) {
            material.iridescenceIOR = ior;
        }
        this[$onUpdate]();
    }
    setIridescenceThicknessMinimum(thicknessMin) {
        this[$ensureMaterialIsLoaded]();
        for (const material of this[$correlatedObjects]) {
            material.iridescenceThicknessRange[0] = thicknessMin;
        }
        this[$onUpdate]();
    }
    setIridescenceThicknessMaximum(thicknessMax) {
        this[$ensureMaterialIsLoaded]();
        for (const material of this[$correlatedObjects]) {
            material.iridescenceThicknessRange[1] = thicknessMax;
        }
        this[$onUpdate]();
    }
    // KHR_materials_anisotropy
    get anisotropyStrength() {
        this[$ensureMaterialIsLoaded]();
        return this[$backingThreeMaterial].anisotropy;
    }
    get anisotropyRotation() {
        this[$ensureMaterialIsLoaded]();
        return this[$backingThreeMaterial].anisotropyRotation;
    }
    get anisotropyTexture() {
        this[$ensureMaterialIsLoaded]();
        return this[$pbrTextures].get(TextureUsage.Anisotropy);
    }
    setAnisotropyStrength(strength) {
        this[$ensureMaterialIsLoaded]();
        for (const material of this[$correlatedObjects]) {
            material.anisotropy = strength;
        }
        this[$onUpdate]();
    }
    setAnisotropyRotation(rotation) {
        this[$ensureMaterialIsLoaded]();
        for (const material of this[$correlatedObjects]) {
            material.anisotropyRotation = rotation;
        }
        this[$onUpdate]();
    }
}
//# sourceMappingURL=material.js.map