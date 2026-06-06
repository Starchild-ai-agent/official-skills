export type Constructor<T = object, U = object> = {
    new (...args: any[]): T;
    prototype: T;
} & U;
export declare const deserializeUrl: (url: string | null) => string | null;
export declare const assertIsArCandidate: () => void;
/**
 * Converts a partial URL string to a fully qualified URL string.
 *
 * @param {String} url
 * @return {String}
 */
export declare const toFullUrl: (partialUrl: string) => string;
/**
 * Returns a throttled version of a given function that is only invoked at most
 * once within a given threshold of time in milliseconds.
 *
 * The throttled version of the function has a "flush" property that resets the
 * threshold for cases when immediate invocation is desired.
 */
export declare const throttle: (fn: (...args: Array<any>) => any, ms: number) => {
    (...args: Array<any>): void;
    flush(): void;
};
export declare const debounce: (fn: (...args: Array<any>) => any, ms: number) => (...args: Array<any>) => void;
/**
 * @param {Number} edge
 * @param {Number} value
 * @return {Number} 0 if value is less than edge, otherwise 1
 */
export declare const step: (edge: number, value: number) => number;
/**
 * @param {Number} value
 * @param {Number} lowerLimit
 * @param {Number} upperLimit
 * @return {Number} value clamped within lowerLimit..upperLimit
 */
export declare const clamp: (value: number, lowerLimit: number, upperLimit: number) => number;
/**
 * Debug mode is enabled when one of the two following conditions is true:
 *
 *  1. A 'model-viewer-debug-mode' query parameter is present in the current
 *     search string
 *  2. There is a global object ModelViewerElement with a debugMode property set
 *     to true
 */
export declare const isDebugMode: () => any;
export type PredicateFunction<T = void> = (value: T) => boolean;
export declare const timePasses: (ms?: number) => Promise<void>;
/**
 * @param {EventTarget|EventDispatcher} target
 * @param {string} eventName
 * @param {?Function} predicate
 */
export declare const waitForEvent: <T>(target: any, eventName: string, predicate?: PredicateFunction<T> | null) => Promise<T>;
