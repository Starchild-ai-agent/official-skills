import { Camera, Mesh, Object3D, XRTargetRaySpace } from 'three';
import { ModelScene } from './ModelScene.js';
import { PlacementBox } from './PlacementBox.js';
export declare class XRMenuPanel extends Object3D {
    private panelMesh;
    private exitButton;
    private toggleButton;
    private goalOpacity;
    private opacityDamper;
    private isActualSize;
    private static readonly iconTextures;
    constructor();
    private createPanel;
    private createButtons;
    private createPanelShape;
    private preRenderIcons;
    private createTextureFromSvg;
    createButton(iconKey: string): Mesh;
    exitButtonControllerIntersection(scene: ModelScene, controller: XRTargetRaySpace): import("three").Intersection<Object3D<import("three").Object3DEventMap>> | undefined;
    scaleModeButtonControllerIntersection(scene: ModelScene, controller: XRTargetRaySpace): import("three").Intersection<Object3D<import("three").Object3DEventMap>> | undefined;
    handleScaleToggle(worldSpaceInitialPlacementDone: boolean, initialModelScale: number, minScale: number, maxScale: number): number | null;
    private updateScaleModeButtonLabel;
    updatePosition(camera: Camera, placementBox: PlacementBox): void;
    /**
     * Set the box's visibility; it will fade in and out.
     */
    set show(visible: boolean);
    /**
     * Call on each frame with the frame delta to fade the box.
     */
    updateOpacity(delta: number): void;
    dispose(): void;
}
