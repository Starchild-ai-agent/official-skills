import { Texture as ThreeTexture } from 'three';
import { Vector2D } from '../../model-viewer-base.js';
import { MagFilter, MinFilter, WrapMode } from '../../three-components/gltf-instance/gltf-2.0.js';
import { Sampler as SamplerInterface, Vector2DInterface } from './api.js';
import { ThreeDOMElement } from './three-dom-element.js';
declare const $threeTexture: unique symbol;
declare const $threeTextures: unique symbol;
declare const $setProperty: unique symbol;
/**
 * Sampler facade implementation for Three.js textures
 */
export declare class Sampler extends ThreeDOMElement implements SamplerInterface {
    private get [$threeTexture]();
    private get [$threeTextures]();
    constructor(onUpdate: () => void, texture: ThreeTexture);
    get name(): string;
    get minFilter(): MinFilter;
    get magFilter(): MagFilter;
    get wrapS(): WrapMode;
    get wrapT(): WrapMode;
    get rotation(): number;
    get scale(): Vector2D;
    get offset(): Vector2D | null;
    setMinFilter(filter: MinFilter): void;
    setMagFilter(filter: MagFilter): void;
    setWrapS(mode: WrapMode): void;
    setWrapT(mode: WrapMode): void;
    setRotation(rotation: number | null): void;
    setScale(scale: Vector2DInterface | null): void;
    setOffset(offset: Vector2DInterface | null): void;
    private [$setProperty];
}
export {};
