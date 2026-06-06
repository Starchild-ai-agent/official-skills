import { Texture as ThreeTexture } from 'three';
import { Texture as TextureInterface } from './api.js';
import { Image } from './image.js';
import { Sampler } from './sampler.js';
import { ThreeDOMElement } from './three-dom-element.js';
declare const $image: unique symbol;
declare const $sampler: unique symbol;
declare const $threeTexture: unique symbol;
/**
 * Material facade implementation for Three.js materials
 */
export declare class Texture extends ThreeDOMElement implements TextureInterface {
    private [$image];
    private [$sampler];
    private get [$threeTexture]();
    constructor(onUpdate: () => void, threeTexture: ThreeTexture);
    get name(): string;
    set name(name: string);
    get sampler(): Sampler;
    get source(): Image;
}
export {};
