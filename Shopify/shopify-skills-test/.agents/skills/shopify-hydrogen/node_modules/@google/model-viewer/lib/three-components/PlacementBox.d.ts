import { Mesh, Vector3, XRTargetRaySpace } from 'three';
import { ModelScene } from './ModelScene.js';
import { Side } from './Shadow.js';
/**
 * Enhanced PlacementBox that dynamically updates based on model size changes
 * and features improved visual design inspired by Footprint.
 */
export declare class PlacementBox extends Mesh {
    private hitPlane;
    private hitBox;
    private shadowHeight;
    private side;
    private goalOpacity;
    private opacityDamper;
    private currentSize;
    private goalSize;
    private sizeDamper;
    private scene;
    private isActive;
    private isHovered;
    private edgeMaterial;
    private fillMaterial;
    private lastGeometryUpdateTime;
    private needsGeometryUpdate;
    constructor(scene: ModelScene, side: Side);
    private updateSizeFromScene;
    private updateGeometry;
    private createHitMeshes;
    private updatePositionFromScene;
    /**
     * Update the placement box when model size changes
     * Optimized to batch updates and reduce performance impact
     */
    updateFromModelChanges(): void;
    /**
     * Ensure the placement box is properly oriented for the current mode
     */
    private ensureProperOrientation;
    /**
     * Set screen space mode to adjust positioning for mobile AR
     */
    setScreenSpaceMode(isScreenSpace: boolean): void;
    private updateHitMeshes;
    /**
     * Set interaction state for visual feedback
     */
    setInteractionState(isActive: boolean, isHovered?: boolean): void;
    private updateVisualState;
    /**
     * Apply distance-based scaling
     */
    applyDistanceScaling(cameraPosition: Vector3): void;
    /**
     * Get the world hit position if the touch coordinates hit the box, and null
     * otherwise. Pass the scene in to get access to its raycaster.
     */
    getHit(scene: ModelScene, screenX: number, screenY: number): Vector3 | null;
    getExpandedHit(scene: ModelScene, screenX: number, screenY: number): Vector3 | null;
    controllerIntersection(scene: ModelScene, controller: XRTargetRaySpace): import("three").Intersection<import("three").Object3D<import("three").Object3DEventMap>> | undefined;
    /**
     * Offset the height of the box relative to the bottom of the scene. Positive
     * is up, so generally only negative values are used.
     */
    set offsetHeight(offset: number);
    get offsetHeight(): number;
    /**
     * Set the box's visibility; it will fade in and out.
     */
    set show(visible: boolean);
    /**
     * Call on each frame with the frame delta to fade the box.
     */
    updateOpacity(delta: number): void;
    /**
     * Update method to be called each frame for smooth transitions
     * Optimized to reduce frequent geometry updates for better performance
     */
    update(delta: number, cameraPosition?: Vector3): void;
    /**
     * Get the current size of the placement box
     */
    getSize(): Vector3;
    /**
     * Call this to clean up Three's cache when you remove the box.
     */
    dispose(): void;
}
