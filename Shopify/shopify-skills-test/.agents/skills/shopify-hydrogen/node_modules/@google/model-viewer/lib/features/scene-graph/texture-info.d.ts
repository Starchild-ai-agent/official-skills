import { MeshPhysicalMaterial, Texture as ThreeTexture } from 'three';
import { TextureInfo as TextureInfoInterface } from './api.js';
import { Texture } from './texture.js';
declare const $texture: unique symbol;
declare const $transform: unique symbol;
export declare const $materials: unique symbol;
export declare const $usage: unique symbol;
declare const $onUpdate: unique symbol;
declare const $activeVideo: unique symbol;
export declare enum TextureUsage {
    Base = 0,
    MetallicRoughness = 1,
    Normal = 2,
    Occlusion = 3,
    Emissive = 4,
    Clearcoat = 5,
    ClearcoatRoughness = 6,
    ClearcoatNormal = 7,
    SheenColor = 8,
    SheenRoughness = 9,
    Transmission = 10,
    Thickness = 11,
    Specular = 12,
    SpecularColor = 13,
    Iridescence = 14,
    IridescenceThickness = 15,
    Anisotropy = 16
}
/**
 * TextureInfo facade implementation for Three.js materials
 */
export declare class TextureInfo implements TextureInfoInterface {
    private [$texture];
    private [$transform];
    private [$materials];
    private [$usage];
    private [$onUpdate];
    private [$activeVideo];
    constructor(onUpdate: () => void, usage: TextureUsage, threeTexture: ThreeTexture | null, material: Set<MeshPhysicalMaterial>);
    get texture(): Texture | null;
    setTexture(texture: Texture | null): void;
}
export {};
