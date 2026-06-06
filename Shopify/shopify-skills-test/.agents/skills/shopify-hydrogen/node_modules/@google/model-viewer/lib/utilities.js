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
import { HAS_WEBXR_DEVICE_API, HAS_WEBXR_HIT_TEST_API, IS_WEBXR_AR_CANDIDATE } from './constants.js';
export const deserializeUrl = (url) => (!!url && url !== 'null') ? toFullUrl(url) : null;
export const assertIsArCandidate = () => {
    if (IS_WEBXR_AR_CANDIDATE) {
        return;
    }
    const missingApis = [];
    if (!HAS_WEBXR_DEVICE_API) {
        missingApis.push('WebXR Device API');
    }
    if (!HAS_WEBXR_HIT_TEST_API) {
        missingApis.push('WebXR Hit Test API');
    }
    throw new Error(`The following APIs are required for AR, but are missing in this browser: ${missingApis.join(', ')}`);
};
/**
 * Converts a partial URL string to a fully qualified URL string.
 *
 * @param {String} url
 * @return {String}
 */
export const toFullUrl = (partialUrl) => {
    const url = new URL(partialUrl, window.location.toString());
    return url.toString();
};
/**
 * Returns a throttled version of a given function that is only invoked at most
 * once within a given threshold of time in milliseconds.
 *
 * The throttled version of the function has a "flush" property that resets the
 * threshold for cases when immediate invocation is desired.
 */
export const throttle = (fn, ms) => {
    let timer = null;
    const throttled = (...args) => {
        if (timer != null) {
            return;
        }
        fn(...args);
        timer = self.setTimeout(() => timer = null, ms);
    };
    throttled.flush = () => {
        if (timer != null) {
            self.clearTimeout(timer);
            timer = null;
        }
    };
    return throttled;
};
export const debounce = (fn, ms) => {
    let timer = null;
    return (...args) => {
        if (timer != null) {
            self.clearTimeout(timer);
        }
        timer = self.setTimeout(() => {
            timer = null;
            fn(...args);
        }, ms);
    };
};
/**
 * @param {Number} edge
 * @param {Number} value
 * @return {Number} 0 if value is less than edge, otherwise 1
 */
export const step = (edge, value) => {
    return value < edge ? 0 : 1;
};
/**
 * @param {Number} value
 * @param {Number} lowerLimit
 * @param {Number} upperLimit
 * @return {Number} value clamped within lowerLimit..upperLimit
 */
export const clamp = (value, lowerLimit, upperLimit) => Math.max(lowerLimit, Math.min(upperLimit, value));
/**
 * Debug mode is enabled when one of the two following conditions is true:
 *
 *  1. A 'model-viewer-debug-mode' query parameter is present in the current
 *     search string
 *  2. There is a global object ModelViewerElement with a debugMode property set
 *     to true
 */
export const isDebugMode = (() => {
    const debugQueryParameterName = 'model-viewer-debug-mode';
    const debugQueryParameter = new RegExp(`[?&]${debugQueryParameterName}(&|$)`);
    return () => (self.ModelViewerElement &&
        self.ModelViewerElement.debugMode) ||
        (self.location && self.location.search &&
            self.location.search.match(debugQueryParameter));
})();
export const timePasses = (ms = 0) => new Promise(resolve => setTimeout(resolve, ms));
/**
 * @param {EventTarget|EventDispatcher} target
 * @param {string} eventName
 * @param {?Function} predicate
 */
export const waitForEvent = (target, eventName, predicate = null) => new Promise(resolve => {
    function handler(event) {
        if (!predicate || predicate(event)) {
            resolve(event);
            target.removeEventListener(eventName, handler);
        }
    }
    target.addEventListener(eventName, handler);
});
//# sourceMappingURL=utilities.js.map