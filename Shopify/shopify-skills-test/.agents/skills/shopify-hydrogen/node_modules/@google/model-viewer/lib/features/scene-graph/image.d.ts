import { Texture as ThreeTexture } from 'three';
import { Image as ImageInterface } from './api.js';
import { ThreeDOMElement } from './three-dom-element.js';
export declare const $threeTexture: unique symbol;
export declare const $threeTextures: unique symbol;
export declare const $applyTexture: unique symbol;
/**
 * Image facade implementation for Three.js textures
 */
export declare class Image extends ThreeDOMElement implements ImageInterface {
    get [$threeTexture](): ThreeTexture;
    get [$threeTextures](): Set<ThreeTexture>;
    constructor(onUpdate: () => void, texture: ThreeTexture);
    get name(): string;
    get uri(): string | undefined;
    get bufferView(): number | undefined;
    get element(): HTMLVideoElement | HTMLCanvasElement | undefined;
    get animation(): any | undefined;
    get type(): 'embedded' | 'external';
    set name(name: string);
    update(): void;
    createThumbnail(width: number, height: number): Promise<string>;
}
