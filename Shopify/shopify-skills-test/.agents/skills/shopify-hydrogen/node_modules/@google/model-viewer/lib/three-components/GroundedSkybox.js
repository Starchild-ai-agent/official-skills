/* @license
 * Copyright 2023 Google LLC. All Rights Reserved.
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
import { Mesh, MeshBasicMaterial, SphereGeometry, Vector3 } from 'three';
export class GroundedSkybox extends Mesh {
    constructor() {
        super(undefined, new MeshBasicMaterial({ depthWrite: false }));
        this.height = 0;
        this.radius = 0;
        this.resolution = 0;
        this.userData.noHit = true;
    }
    get map() {
        return this.material.map;
    }
    set map(skybox) {
        this.material.map = skybox;
    }
    isUsable() {
        return this.height > 0 && this.radius > 0 && this.geometry != null &&
            this.map != null;
    }
    updateGeometry(height = this.height, radius = this.radius, resolution = 128) {
        if (height != this.height || radius != this.radius ||
            resolution != this.resolution) {
            this.height = height;
            this.radius = radius;
            this.resolution = resolution;
            if (height > 0 && radius > 0) {
                this.geometry.dispose();
                this.geometry = makeGeometry(height, radius, resolution);
            }
        }
    }
}
function makeGeometry(height, radius, resolution) {
    const geometry = new SphereGeometry(radius, 2 * resolution, resolution);
    geometry.scale(1, 1, -1);
    const pos = geometry.getAttribute('position');
    const tmp = new Vector3();
    for (let i = 0; i < pos.count; ++i) {
        tmp.fromBufferAttribute(pos, i);
        if (tmp.y < 0) {
            // Smooth out the transition from flat floor to sphere:
            const y1 = -height * 3 / 2;
            const f = tmp.y < y1 ? -height / tmp.y : (1 - tmp.y * tmp.y / (3 * y1 * y1));
            tmp.multiplyScalar(f);
            tmp.toArray(pos.array, 3 * i);
        }
    }
    pos.needsUpdate = true;
    return geometry;
}
//# sourceMappingURL=GroundedSkybox.js.map