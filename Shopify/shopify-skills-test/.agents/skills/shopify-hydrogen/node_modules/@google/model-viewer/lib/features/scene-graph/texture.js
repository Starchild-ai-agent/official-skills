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
import { Image } from './image.js';
import { Sampler } from './sampler.js';
import { $correlatedObjects, ThreeDOMElement } from './three-dom-element.js';
const $image = Symbol('image');
const $sampler = Symbol('sampler');
const $threeTexture = Symbol('threeTexture');
/**
 * Material facade implementation for Three.js materials
 */
export class Texture extends ThreeDOMElement {
    get [$threeTexture]() {
        var _a;
        return (_a = this[$correlatedObjects]) === null || _a === void 0 ? void 0 : _a.values().next().value;
    }
    constructor(onUpdate, threeTexture) {
        super(onUpdate, new Set(threeTexture ? [threeTexture] : []));
        this[$sampler] = new Sampler(onUpdate, threeTexture);
        this[$image] = new Image(onUpdate, threeTexture);
    }
    get name() {
        return this[$threeTexture].name || '';
    }
    set name(name) {
        for (const texture of this[$correlatedObjects]) {
            texture.name = name;
        }
    }
    get sampler() {
        return this[$sampler];
    }
    get source() {
        return this[$image];
    }
}
//# sourceMappingURL=texture.js.map