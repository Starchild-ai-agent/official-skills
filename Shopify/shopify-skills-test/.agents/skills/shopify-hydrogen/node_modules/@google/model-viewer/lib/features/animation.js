/* @license
 * Copyright 2019 Google LLC. All Rights Reserved.
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
var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
import { property } from 'lit/decorators.js';
import { LoopOnce, LoopPingPong, LoopRepeat } from 'three';
import { $getModelIsVisible, $needsRender, $onModelLoad, $renderer, $scene, $tick } from '../model-viewer-base.js';
const MILLISECONDS_PER_SECOND = 1000.0;
const $changeAnimation = Symbol('changeAnimation');
const $appendAnimation = Symbol('appendAnimation');
const $detachAnimation = Symbol('detachAnimation');
const $paused = Symbol('paused');
const DEFAULT_PLAY_OPTIONS = {
    repetitions: Infinity,
    pingpong: false
};
const DEFAULT_APPEND_OPTIONS = {
    pingpong: false,
    repetitions: null,
    weight: 1,
    timeScale: 1,
    fade: false,
    warp: false,
    relativeWarp: true,
    time: null
};
const DEFAULT_DETACH_OPTIONS = {
    fade: true
};
export const AnimationMixin = (ModelViewerElement) => {
    var _a;
    class AnimationModelViewerElement extends ModelViewerElement {
        constructor(...args) {
            super(args);
            this.autoplay = false;
            this.animationName = undefined;
            this.animationCrossfadeDuration = 300;
            this[_a] = true;
            this[$scene].subscribeMixerEvent('loop', (e) => {
                const count = e.action._loopCount;
                const name = e.action._clip.name;
                const uuid = e.action._clip.uuid;
                const targetAnimation = this[$scene].markedAnimations.find(e => e.name === name);
                if (targetAnimation) {
                    this[$scene].updateAnimationLoop(targetAnimation.name, targetAnimation.loopMode, targetAnimation.repetitionCount);
                    const filtredArr = this[$scene].markedAnimations.filter(e => e.name !== name);
                    this[$scene].markedAnimations = filtredArr;
                }
                this.dispatchEvent(new CustomEvent('loop', { detail: { count, name, uuid } }));
            });
            this[$scene].subscribeMixerEvent('finished', (e) => {
                if (!this[$scene].appendedAnimations.includes(e.action._clip.name)) {
                    this[$paused] = true;
                }
                else {
                    const filteredList = this[$scene].appendedAnimations.filter(i => i !== e.action._clip.name);
                    this[$scene].appendedAnimations = filteredList;
                }
                this.dispatchEvent(new CustomEvent('finished'));
            });
        }
        /**
         * Returns an array
         */
        get availableAnimations() {
            if (this.loaded) {
                return this[$scene].animationNames;
            }
            return [];
        }
        get duration() {
            return this[$scene].duration;
        }
        get paused() {
            return this[$paused];
        }
        get currentTime() {
            return this[$scene].animationTime;
        }
        get appendedAnimations() {
            return this[$scene].appendedAnimations;
        }
        set currentTime(value) {
            this[$scene].animationTime = value;
            this[$needsRender]();
        }
        get timeScale() {
            return this[$scene].animationTimeScale;
        }
        set timeScale(value) {
            this[$scene].animationTimeScale = value;
        }
        pause() {
            if (this[$paused]) {
                return;
            }
            this[$paused] = true;
            this.dispatchEvent(new CustomEvent('pause'));
        }
        play(options) {
            if (this.availableAnimations.length > 0) {
                this[$paused] = false;
                this[$changeAnimation](options);
                this.dispatchEvent(new CustomEvent('play'));
            }
        }
        appendAnimation(animationName, options) {
            if (this.availableAnimations.length > 0) {
                this[$paused] = false;
                this[$appendAnimation](animationName, options);
                this.dispatchEvent(new CustomEvent('append-animation'));
            }
        }
        detachAnimation(animationName, options) {
            if (this.availableAnimations.length > 0) {
                this[$paused] = false;
                this[$detachAnimation](animationName, options);
                this.dispatchEvent(new CustomEvent('detach-animation'));
            }
        }
        [(_a = $paused, $onModelLoad)]() {
            super[$onModelLoad]();
            this[$paused] = true;
            if (this.animationName != null) {
                this[$changeAnimation]();
            }
            if (this.autoplay) {
                this.play();
            }
        }
        [$tick](_time, delta) {
            super[$tick](_time, delta);
            if (this[$paused] ||
                (!this[$getModelIsVisible]() && !this[$renderer].isPresenting)) {
                return;
            }
            this[$scene].updateAnimation(delta / MILLISECONDS_PER_SECOND);
            this[$needsRender]();
        }
        updated(changedProperties) {
            super.updated(changedProperties);
            if (changedProperties.has('autoplay') && this.autoplay) {
                this.play();
            }
            if (changedProperties.has('animationName')) {
                this[$changeAnimation]();
            }
        }
        [$changeAnimation](options = DEFAULT_PLAY_OPTIONS) {
            var _b;
            const repetitions = (_b = options.repetitions) !== null && _b !== void 0 ? _b : Infinity;
            const mode = options.pingpong ?
                LoopPingPong :
                (repetitions === 1 ? LoopOnce : LoopRepeat);
            this[$scene].playAnimation(this.animationName, this.animationCrossfadeDuration / MILLISECONDS_PER_SECOND, mode, repetitions);
            // If we are currently paused, we need to force a render so that
            // the scene updates to the first frame of the new animation
            if (this[$paused]) {
                this[$scene].updateAnimation(0);
                this[$needsRender]();
            }
        }
        [$appendAnimation](animationName = '', options = DEFAULT_APPEND_OPTIONS) {
            var _b;
            const repetitions = (_b = options.repetitions) !== null && _b !== void 0 ? _b : Infinity;
            const mode = options.pingpong ?
                LoopPingPong :
                (repetitions === 1 ? LoopOnce : LoopRepeat);
            const needsToStop = !!options.repetitions || 'pingpong' in options;
            this[$scene].appendAnimation(animationName ? animationName : this.animationName, mode, repetitions, options.weight, options.timeScale, options.fade, options.warp, options.relativeWarp, options.time, needsToStop);
            // If we are currently paused, we need to force a render so that
            // the scene updates to the first frame of the new animation
            if (this[$paused]) {
                this[$scene].updateAnimation(0);
                this[$needsRender]();
            }
        }
        [$detachAnimation](animationName = '', options = DEFAULT_DETACH_OPTIONS) {
            this[$scene].detachAnimation(animationName ? animationName : this.animationName, options.fade);
            // If we are currently paused, we need to force a render so that
            // the scene updates to the first frame of the new animation
            if (this[$paused]) {
                this[$scene].updateAnimation(0);
                this[$needsRender]();
            }
        }
    }
    __decorate([
        property({ type: Boolean })
    ], AnimationModelViewerElement.prototype, "autoplay", void 0);
    __decorate([
        property({ type: String, attribute: 'animation-name' })
    ], AnimationModelViewerElement.prototype, "animationName", void 0);
    __decorate([
        property({ type: Number, attribute: 'animation-crossfade-duration' })
    ], AnimationModelViewerElement.prototype, "animationCrossfadeDuration", void 0);
    return AnimationModelViewerElement;
};
//# sourceMappingURL=animation.js.map