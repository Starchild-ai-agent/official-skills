import { $getLoadedMaterial, $variantIndices } from '../material.js';
import { $correlatedObjects } from '../three-dom-element.js';
// Defines the base level node methods and data.
export class Node {
    constructor(name) {
        this.name = '';
        this.children = new Array();
        this.name = name;
    }
}
// Represents a primitive in a glTF mesh.
export class PrimitiveNode extends Node {
    constructor(mesh, mvMaterials, modelVariants, correlatedSceneGraph) {
        super(mesh.name);
        // Maps glTF material index number to a material that this primitive supports.
        this.materials = new Map();
        // Maps variant index to material.
        this.variantToMaterialMap = new Map();
        this.initialMaterialIdx = 0;
        this.activeMaterialIdx = 0;
        this.mesh = mesh;
        const { gltf, threeGLTF, threeObjectMap } = correlatedSceneGraph;
        this.parser = threeGLTF.parser;
        this.modelVariants = modelVariants;
        this.mesh.userData.variantData = modelVariants;
        // Captures the primitive's initial material.
        const materialMappings = threeObjectMap.get(mesh.material);
        if (materialMappings.materials != null) {
            this.initialMaterialIdx = this.activeMaterialIdx =
                materialMappings.materials;
        }
        else {
            console.error(`Primitive (${mesh.name}) missing initial material reference.`);
        }
        // Gets the mesh index from the node.
        const associations = mesh.userData.associations ||
            {};
        if (associations.meshes == null) {
            console.error('Mesh is missing primitive index association');
            return;
        }
        // The gltf mesh array to sample from.
        const meshElementArray = gltf['meshes'] || [];
        // List of primitives under the mesh.
        const gltfPrimitives = (meshElementArray[associations.meshes].primitives || []);
        const gltfPrimitive = gltfPrimitives[associations.primitives];
        if (gltfPrimitive == null) {
            console.error('Mesh primitive definition is missing.');
            return;
        }
        // Maps the gltfPrimitive default to a material.
        if (gltfPrimitive.material != null) {
            this.materials.set(gltfPrimitive.material, mvMaterials[gltfPrimitive.material]);
        }
        else {
            const defaultIdx = mvMaterials.findIndex((mat) => {
                return mat.name === 'Default';
            });
            if (defaultIdx >= 0) {
                this.materials.set(defaultIdx, mvMaterials[defaultIdx]);
            }
            else {
                console.warn('gltfPrimitive has no material!');
            }
        }
        if (gltfPrimitive.extensions &&
            gltfPrimitive.extensions['KHR_materials_variants']) {
            const variantsExtension = gltfPrimitive.extensions['KHR_materials_variants'];
            const extensions = threeGLTF.parser.json.extensions;
            const variantNames = extensions['KHR_materials_variants'].variants;
            // Provides definition now that we know there are variants to
            // support.
            for (const mapping of variantsExtension.mappings) {
                const mvMaterial = mvMaterials[mapping.material];
                // Maps variant indices to Materials.
                this.materials.set(mapping.material, mvMaterial);
                for (const variant of mapping.variants) {
                    const { name } = variantNames[variant];
                    this.variantToMaterialMap.set(variant, mvMaterial);
                    // Provides variant info for material self lookup.
                    mvMaterial[$variantIndices].add(variant);
                    // Updates the models variant data.
                    if (!modelVariants.has(name)) {
                        modelVariants.set(name, { name, index: variant });
                    }
                }
            }
        }
    }
    async setActiveMaterial(material) {
        const mvMaterial = this.materials.get(material);
        if (material !== this.activeMaterialIdx) {
            const backingMaterials = mvMaterial[$correlatedObjects];
            const baseMaterial = await mvMaterial[$getLoadedMaterial]();
            if (baseMaterial != null) {
                this.mesh.material = baseMaterial;
            }
            else {
                this.mesh.material = backingMaterials.values().next().value;
            }
            this.parser.assignFinalMaterial(this.mesh);
            backingMaterials.add(this.mesh.material);
            this.activeMaterialIdx = material;
        }
        return this.mesh.material;
    }
    getActiveMaterial() {
        return this.materials.get(this.activeMaterialIdx);
    }
    getMaterial(index) {
        return this.materials.get(index);
    }
    async enableVariant(name) {
        if (name == null) {
            return this.setActiveMaterial(this.initialMaterialIdx);
        }
        if (this.variantToMaterialMap != null && this.modelVariants.has(name)) {
            const modelVariants = this.modelVariants.get(name);
            return this.enableVariantHelper(modelVariants.index);
        }
        return null;
    }
    async enableVariantHelper(index) {
        if (this.variantToMaterialMap != null && index != null) {
            const material = this.variantToMaterialMap.get(index);
            if (material != null) {
                return this.setActiveMaterial(material.index);
            }
        }
        return null;
    }
    async instantiateVariants() {
        if (this.variantToMaterialMap == null) {
            return;
        }
        for (const index of this.variantToMaterialMap.keys()) {
            const variantMaterial = this.mesh.userData.variantMaterials.get(index);
            if (variantMaterial.material != null) {
                continue;
            }
            const threeMaterial = await this.enableVariantHelper(index);
            if (threeMaterial != null) {
                variantMaterial.material = threeMaterial;
            }
        }
    }
    get variantInfo() {
        return this.variantToMaterialMap;
    }
    addVariant(materialVariant, variantName) {
        if (!this.ensureVariantIsUnused(variantName)) {
            return false;
        }
        // Adds the variant to the model variants if needed.
        if (!this.modelVariants.has(variantName)) {
            this.modelVariants.set(variantName, { name: variantName, index: this.modelVariants.size });
        }
        const modelVariantData = this.modelVariants.get(variantName);
        const variantIndex = modelVariantData.index;
        // Updates materials mapped to the variant.
        materialVariant[$variantIndices].add(variantIndex);
        // Updates internal mappings.
        this.variantToMaterialMap.set(variantIndex, materialVariant);
        this.materials.set(materialVariant.index, materialVariant);
        this.updateVariantUserData(variantIndex, materialVariant);
        return true;
    }
    deleteVariant(variantIndex) {
        if (this.variantInfo.has(variantIndex)) {
            this.variantInfo.delete(variantIndex);
            const userDataMap = this.mesh.userData.variantMaterials;
            if (userDataMap != null) {
                userDataMap.delete(variantIndex);
            }
        }
    }
    updateVariantUserData(variantIndex, materialVariant) {
        // Adds variants name to material variants set.
        materialVariant[$variantIndices].add(variantIndex);
        this.mesh.userData.variantData = this.modelVariants;
        // Updates import data (see VariantMaterialLoaderPlugin.ts).
        this.mesh.userData.variantMaterials = this.mesh.userData.variantMaterials ||
            new Map();
        const map = this.mesh.userData.variantMaterials;
        map.set(variantIndex, {
            material: materialVariant[$correlatedObjects].values().next().value,
            gltfMaterialIndex: materialVariant.index,
        });
    }
    ensureVariantIsUnused(variantName) {
        const modelVariants = this.modelVariants.get(variantName);
        if (modelVariants != null && this.variantInfo.has(modelVariants.index)) {
            console.warn(`Primitive cannot add variant '${variantName}' for this material, it already exists.`);
            return false;
        }
        return true;
    }
}
//# sourceMappingURL=primitive-node.js.map