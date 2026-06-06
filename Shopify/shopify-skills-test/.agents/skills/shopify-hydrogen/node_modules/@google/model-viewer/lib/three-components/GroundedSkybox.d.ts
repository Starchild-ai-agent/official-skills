import { Mesh, Texture } from 'three';
export declare class GroundedSkybox extends Mesh {
    private height;
    private radius;
    private resolution;
    constructor();
    get map(): Texture | null;
    set map(skybox: Texture | null);
    isUsable(): boolean;
    updateGeometry(height?: number, radius?: number, resolution?: number): void;
}
