import { MeshBasicMaterial, Scene } from 'three';
export default class EnvironmentScene extends Scene {
    constructor(name: 'legacy' | 'neutral');
    createAreaLightMaterial(intensity: number): MeshBasicMaterial;
}
