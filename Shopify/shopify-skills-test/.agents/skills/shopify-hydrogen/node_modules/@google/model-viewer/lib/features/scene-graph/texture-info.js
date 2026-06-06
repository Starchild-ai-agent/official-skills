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
var _a, _b, _c;
import { LinearSRGBColorSpace, SRGBColorSpace, Vector2 } from 'three';
import { $threeTexture } from './image.js';
import { Texture } from './texture.js';
const $texture = Symbol('texture');
const $transform = Symbol('transform');
export const $materials = Symbol('materials');
export const $usage = Symbol('usage');
const $onUpdate = Symbol('onUpdate');
const $activeVideo = Symbol('activeVideo');
// Defines what a texture will be used for.
export var TextureUsage;
(function (TextureUsage) {
    TextureUsage[TextureUsage["Base"] = 0] = "Base";
    TextureUsage[TextureUsage["MetallicRoughness"] = 1] = "MetallicRoughness";
    TextureUsage[TextureUsage["Normal"] = 2] = "Normal";
    TextureUsage[TextureUsage["Occlusion"] = 3] = "Occlusion";
    TextureUsage[TextureUsage["Emissive"] = 4] = "Emissive";
    TextureUsage[TextureUsage["Clearcoat"] = 5] = "Clearcoat";
    TextureUsage[TextureUsage["ClearcoatRoughness"] = 6] = "ClearcoatRoughness";
    TextureUsage[TextureUsage["ClearcoatNormal"] = 7] = "ClearcoatNormal";
    TextureUsage[TextureUsage["SheenColor"] = 8] = "SheenColor";
    TextureUsage[TextureUsage["SheenRoughness"] = 9] = "SheenRoughness";
    TextureUsage[TextureUsage["Transmission"] = 10] = "Transmission";
    TextureUsage[TextureUsage["Thickness"] = 11] = "Thickness";
    TextureUsage[TextureUsage["Specular"] = 12] = "Specular";
    TextureUsage[TextureUsage["SpecularColor"] = 13] = "SpecularColor";
    TextureUsage[TextureUsage["Iridescence"] = 14] = "Iridescence";
    TextureUsage[TextureUsage["IridescenceThickness"] = 15] = "IridescenceThickness";
    TextureUsage[TextureUsage["Anisotropy"] = 16] = "Anisotropy";
})(TextureUsage || (TextureUsage = {}));
/**
 * TextureInfo facade implementation for Three.js materials
 */
export class TextureInfo {
    constructor(onUpdate, usage, threeTexture, material) {
        this[_a] = null;
        this[_b] = {
            rotation: 0,
            scale: new Vector2(1, 1),
            offset: new Vector2(0, 0)
        };
        this[_c] = false;
        // Creates image, sampler, and texture if valid texture info is provided.
        if (threeTexture) {
            this[$transform].rotation = threeTexture.rotation;
            this[$transform].scale.copy(threeTexture.repeat);
            this[$transform].offset.copy(threeTexture.offset);
            this[$texture] = new Texture(onUpdate, threeTexture);
        }
        this[$onUpdate] = onUpdate;
        this[$materials] = material;
        this[$usage] = usage;
    }
    get texture() {
        return this[$texture];
    }
    setTexture(texture) {
        var _d, _e;
        const threeTexture = texture != null ? texture.source[$threeTexture] : null;
        const oldTexture = (_d = this[$texture]) === null || _d === void 0 ? void 0 : _d.source[$threeTexture];
        if (oldTexture != null && oldTexture.isVideoTexture) {
            this[$activeVideo] = false;
        }
        else if ((_e = this[$texture]) === null || _e === void 0 ? void 0 : _e.source.animation) {
            this[$texture].source.animation.removeEventListener('enterFrame', this[$onUpdate]);
        }
        this[$texture] = texture;
        if (threeTexture != null && threeTexture.isVideoTexture) {
            const element = threeTexture.image;
            this[$activeVideo] = true;
            if (element.requestVideoFrameCallback != null) {
                const update = () => {
                    if (!this[$activeVideo]) {
                        return;
                    }
                    this[$onUpdate]();
                    element.requestVideoFrameCallback(update);
                };
                element.requestVideoFrameCallback(update);
            }
            else {
                const update = () => {
                    if (!this[$activeVideo]) {
                        return;
                    }
                    this[$onUpdate]();
                    requestAnimationFrame(update);
                };
                requestAnimationFrame(update);
            }
        }
        else if ((texture === null || texture === void 0 ? void 0 : texture.source.animation) != null) {
            texture.source.animation.addEventListener('enterFrame', this[$onUpdate]);
        }
        let colorSpace = SRGBColorSpace;
        if (this[$materials]) {
            for (const material of this[$materials]) {
                switch (this[$usage]) {
                    case TextureUsage.Base:
                        material.map = threeTexture;
                        break;
                    case TextureUsage.MetallicRoughness:
                        colorSpace = LinearSRGBColorSpace;
                        material.metalnessMap = threeTexture;
                        material.roughnessMap = threeTexture;
                        break;
                    case TextureUsage.Normal:
                        colorSpace = LinearSRGBColorSpace;
                        material.normalMap = threeTexture;
                        break;
                    case TextureUsage.Occlusion:
                        colorSpace = LinearSRGBColorSpace;
                        material.aoMap = threeTexture;
                        break;
                    case TextureUsage.Emissive:
                        material.emissiveMap = threeTexture;
                        break;
                    case TextureUsage.Clearcoat:
                        material.clearcoatMap = threeTexture;
                        break;
                    case TextureUsage.ClearcoatRoughness:
                        material.clearcoatRoughnessMap = threeTexture;
                        break;
                    case TextureUsage.ClearcoatNormal:
                        material.clearcoatNormalMap = threeTexture;
                        break;
                    case TextureUsage.SheenColor:
                        material.sheenColorMap = threeTexture;
                        break;
                    case TextureUsage.SheenRoughness:
                        material.sheenRoughnessMap = threeTexture;
                        break;
                    case TextureUsage.Transmission:
                        material.transmissionMap = threeTexture;
                        break;
                    case TextureUsage.Thickness:
                        material.thicknessMap = threeTexture;
                        break;
                    case TextureUsage.Specular:
                        material.specularIntensityMap = threeTexture;
                        break;
                    case TextureUsage.SpecularColor:
                        material.specularColorMap = threeTexture;
                        break;
                    case TextureUsage.Iridescence:
                        material.iridescenceMap = threeTexture;
                        break;
                    case TextureUsage.IridescenceThickness:
                        material.iridescenceThicknessMap = threeTexture;
                        break;
                    case TextureUsage.Anisotropy:
                        material.anisotropyMap = threeTexture;
                        break;
                    default:
                }
                material.needsUpdate = true;
            }
        }
        if (threeTexture) {
            // Updates the colorSpace for the texture, affects all references.
            threeTexture.colorSpace = colorSpace;
            threeTexture.rotation = this[$transform].rotation;
            threeTexture.repeat = this[$transform].scale;
            threeTexture.offset = this[$transform].offset;
        }
        this[$onUpdate]();
    }
}
_a = $texture, _b = $transform, _c = $activeVideo;
//# sourceMappingURL=texture-info.js.map