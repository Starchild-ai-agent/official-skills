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
import { ClampToEdgeWrapping, LinearFilter, LinearMipmapLinearFilter, LinearMipmapNearestFilter, MirroredRepeatWrapping, NearestFilter, NearestMipmapLinearFilter, NearestMipmapNearestFilter, RepeatWrapping, Vector2 } from 'three';
import { toVector2D } from '../../model-viewer-base.js';
import { Filter, Wrap } from '../../three-components/gltf-instance/gltf-2.0.js';
import { $correlatedObjects, $onUpdate, ThreeDOMElement } from './three-dom-element.js';
// Convertion between gltf standards and threejs standards.
const wrapModeToWrapping = new Map([
    [Wrap.Repeat, RepeatWrapping],
    [Wrap.ClampToEdge, ClampToEdgeWrapping],
    [Wrap.MirroredRepeat, MirroredRepeatWrapping]
]);
const wrappingToWrapMode = new Map([
    [RepeatWrapping, Wrap.Repeat],
    [ClampToEdgeWrapping, Wrap.ClampToEdge],
    [MirroredRepeatWrapping, Wrap.MirroredRepeat]
]);
const minFilterToMinification = new Map([
    [Filter.Nearest, NearestFilter],
    [Filter.Linear, LinearFilter],
    [Filter.NearestMipmapNearest, NearestMipmapNearestFilter],
    [Filter.LinearMipmapNearest, LinearMipmapNearestFilter],
    [Filter.NearestMipmapLinear, NearestMipmapLinearFilter],
    [Filter.LinearMipmapLinear, LinearMipmapLinearFilter]
]);
const minificationToMinFilter = new Map([
    [NearestFilter, Filter.Nearest],
    [LinearFilter, Filter.Linear],
    [NearestMipmapNearestFilter, Filter.NearestMipmapNearest],
    [LinearMipmapNearestFilter, Filter.LinearMipmapNearest],
    [NearestMipmapLinearFilter, Filter.NearestMipmapLinear],
    [LinearMipmapLinearFilter, Filter.LinearMipmapLinear]
]);
const magFilterToMagnification = new Map([[Filter.Nearest, NearestFilter], [Filter.Linear, LinearFilter]]);
const magnificationToMagFilter = new Map([[NearestFilter, Filter.Nearest], [LinearFilter, Filter.Linear]]);
// Checks for threejs standards.
const isMinFilter = (() => {
    return (value) => minificationToMinFilter.has(value);
})();
const isMagFilter = (() => {
    return (value) => magnificationToMagFilter.has(value);
})();
const isWrapping = (() => {
    return (value) => wrappingToWrapMode.has(value);
})();
const isValidSamplerValue = (property, value) => {
    switch (property) {
        case 'minFilter':
            return isMinFilter(value);
        case 'magFilter':
            return isMagFilter(value);
        case 'wrapS':
        case 'wrapT':
            return isWrapping(value);
        case 'rotation':
        case 'repeat':
        case 'offset':
            return true;
        default:
            throw new Error(`Cannot configure property "${property}" on Sampler`);
    }
};
const $threeTexture = Symbol('threeTexture');
const $threeTextures = Symbol('threeTextures');
const $setProperty = Symbol('setProperty');
/**
 * Sampler facade implementation for Three.js textures
 */
export class Sampler extends ThreeDOMElement {
    get [$threeTexture]() {
        var _a;
        return (_a = this[$correlatedObjects]) === null || _a === void 0 ? void 0 : _a.values().next().value;
    }
    get [$threeTextures]() {
        return this[$correlatedObjects];
    }
    constructor(onUpdate, texture) {
        super(onUpdate, new Set(texture ? [texture] : []));
    }
    get name() {
        return this[$threeTexture].name || '';
    }
    get minFilter() {
        return minificationToMinFilter.get(this[$threeTexture].minFilter);
    }
    get magFilter() {
        return magnificationToMagFilter.get(this[$threeTexture].magFilter);
    }
    get wrapS() {
        return wrappingToWrapMode.get(this[$threeTexture].wrapS);
    }
    get wrapT() {
        return wrappingToWrapMode.get(this[$threeTexture].wrapT);
    }
    get rotation() {
        return this[$threeTexture].rotation;
    }
    get scale() {
        return toVector2D(this[$threeTexture].repeat);
    }
    get offset() {
        return toVector2D(this[$threeTexture].offset);
    }
    setMinFilter(filter) {
        this[$setProperty]('minFilter', minFilterToMinification.get(filter));
    }
    setMagFilter(filter) {
        this[$setProperty]('magFilter', magFilterToMagnification.get(filter));
    }
    setWrapS(mode) {
        this[$setProperty]('wrapS', wrapModeToWrapping.get(mode));
    }
    setWrapT(mode) {
        this[$setProperty]('wrapT', wrapModeToWrapping.get(mode));
    }
    setRotation(rotation) {
        if (rotation == null) {
            // Reset rotation.
            rotation = 0;
        }
        this[$setProperty]('rotation', rotation);
    }
    setScale(scale) {
        if (scale == null) {
            // Reset scale.
            scale = { u: 1, v: 1 };
        }
        this[$setProperty]('repeat', new Vector2(scale.u, scale.v));
    }
    setOffset(offset) {
        if (offset == null) {
            // Reset offset.
            offset = { u: 0, v: 0 };
        }
        this[$setProperty]('offset', new Vector2(offset.u, offset.v));
    }
    [$setProperty](property, value) {
        if (isValidSamplerValue(property, value)) {
            for (const texture of this[$threeTextures]) {
                texture[property] = value;
                texture.needsUpdate = true;
            }
        }
        this[$onUpdate]();
    }
}
//# sourceMappingURL=sampler.js.map