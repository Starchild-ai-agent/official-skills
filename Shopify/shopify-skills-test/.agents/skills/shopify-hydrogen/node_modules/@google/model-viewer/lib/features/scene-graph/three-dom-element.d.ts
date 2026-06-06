import { Material, Object3D, Texture } from 'three';
export declare const $correlatedObjects: unique symbol;
export declare const $onUpdate: unique symbol;
type CorrelatedObjects = Set<Object3D> | Set<Material> | Set<Texture>;
/**
 * A SerializableThreeDOMElement is the common primitive of all scene graph
 * elements that have been facaded in the host execution context. It adds
 * a common interface to these elements in support of convenient
 * serializability.
 */
export declare class ThreeDOMElement {
    readonly [$onUpdate]: () => void;
    [$correlatedObjects]: CorrelatedObjects;
    constructor(onUpdate: () => void, correlatedObjects: CorrelatedObjects);
}
export {};
