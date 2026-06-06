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
import { Color } from 'three';
import { TextureInfo, TextureUsage } from './texture-info.js';
import { $correlatedObjects, $onUpdate, ThreeDOMElement } from './three-dom-element.js';
const $threeMaterial = Symbol('threeMaterial');
const $threeMaterials = Symbol('threeMaterials');
const $baseColorTexture = Symbol('baseColorTexture');
const $metallicRoughnessTexture = Symbol('metallicRoughnessTexture');
/**
 * PBR material properties facade implementation for Three.js materials
 */
export class PBRMetallicRoughness extends ThreeDOMElement {
    get [$threeMaterials]() {
        return this[$correlatedObjects];
    }
    get [$threeMaterial]() {
        var _a;
        return (_a = this[$correlatedObjects]) === null || _a === void 0 ? void 0 : _a.values().next().value;
    }
    constructor(onUpdate, correlatedMaterials) {
        super(onUpdate, correlatedMaterials);
        const { map, metalnessMap } = correlatedMaterials.values().next().value;
        this[$baseColorTexture] =
            new TextureInfo(onUpdate, TextureUsage.Base, map, correlatedMaterials);
        this[$metallicRoughnessTexture] = new TextureInfo(onUpdate, TextureUsage.MetallicRoughness, metalnessMap, correlatedMaterials);
    }
    get baseColorFactor() {
        const rgba = [0, 0, 0, this[$threeMaterial].opacity];
        this[$threeMaterial].color.toArray(rgba);
        return rgba;
    }
    get metallicFactor() {
        return this[$threeMaterial].metalness;
    }
    get roughnessFactor() {
        return this[$threeMaterial].roughness;
    }
    get baseColorTexture() {
        return this[$baseColorTexture];
    }
    get metallicRoughnessTexture() {
        return this[$metallicRoughnessTexture];
    }
    setBaseColorFactor(rgba) {
        const color = new Color();
        if (rgba instanceof Array) {
            color.fromArray(rgba);
        }
        else {
            color.set(rgba);
        }
        for (const material of this[$threeMaterials]) {
            material.color.set(color);
            if (rgba instanceof Array && rgba.length > 3) {
                material.opacity = rgba[3];
            }
            else {
                rgba = [0, 0, 0, material.opacity];
                color.toArray(rgba);
            }
        }
        this[$onUpdate]();
    }
    setMetallicFactor(value) {
        for (const material of this[$threeMaterials]) {
            material.metalness = value;
        }
        this[$onUpdate]();
    }
    setRoughnessFactor(value) {
        for (const material of this[$threeMaterials]) {
            material.roughness = value;
        }
        this[$onUpdate]();
    }
}
//# sourceMappingURL=pbr-metallic-roughness.js.map