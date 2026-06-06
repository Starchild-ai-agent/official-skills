import { Material as ThreeMaterial, Mesh } from 'three';
import { CorrelatedSceneGraph } from '../../../three-components/gltf-instance/correlated-scene-graph.js';
import { Material } from '../material.js';
import { VariantData } from '../model.js';
export declare class Node {
    name: string;
    children: Node[];
    constructor(name: string);
}
export declare class PrimitiveNode extends Node {
    mesh: Mesh;
    materials: Map<number, Material>;
    private variantToMaterialMap;
    initialMaterialIdx: number;
    private activeMaterialIdx;
    private modelVariants;
    private parser;
    constructor(mesh: Mesh, mvMaterials: Material[], modelVariants: Map<string, VariantData>, correlatedSceneGraph: CorrelatedSceneGraph);
    setActiveMaterial(material: number): Promise<ThreeMaterial | null>;
    getActiveMaterial(): Material;
    getMaterial(index: number): Material | undefined;
    enableVariant(name: string | null): Promise<ThreeMaterial | null>;
    private enableVariantHelper;
    instantiateVariants(): Promise<void>;
    get variantInfo(): Map<number, Material>;
    addVariant(materialVariant: Material, variantName: string): boolean;
    deleteVariant(variantIndex: number): void;
    private updateVariantUserData;
    private ensureVariantIsUnused;
}
