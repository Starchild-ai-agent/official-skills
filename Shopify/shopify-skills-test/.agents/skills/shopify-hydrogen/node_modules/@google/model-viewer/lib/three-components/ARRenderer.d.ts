import { Event as ThreeEvent, EventDispatcher, Vector3, WebGLRenderer } from 'three';
import { ModelScene } from './ModelScene.js';
import { Renderer } from './Renderer.js';
export type ARStatus = 'not-presenting' | 'session-started' | 'object-placed' | 'failed';
export declare const ARStatus: {
    [index: string]: ARStatus;
};
export interface ARStatusEvent extends ThreeEvent {
    status: ARStatus;
}
export type ARTracking = 'tracking' | 'not-tracking';
export declare const ARTracking: {
    [index: string]: ARTracking;
};
export interface ARTrackingEvent extends ThreeEvent {
    status: ARTracking;
}
export declare const XRMode: {
    readonly SCREEN_SPACE: "screen-space";
    readonly WORLD_SPACE: "world-space";
};
export type XRMode = typeof XRMode[keyof typeof XRMode];
export declare class ARRenderer extends EventDispatcher<{
    status: {
        status: ARStatus;
    };
    tracking: {
        status: ARTracking;
    };
}> {
    private renderer;
    threeRenderer: WebGLRenderer;
    currentSession: XRSession | null;
    placeOnWall: boolean;
    private placementBox;
    private menuPanel;
    private lastTick;
    private turntableRotation;
    private oldShadowIntensity;
    private frame;
    private initialHitSource;
    private transientHitTestSource;
    private inputSource;
    private _presentedScene;
    private resolveCleanup;
    private exitWebXRButtonContainer;
    private overlay;
    private xrLight;
    private xrMode;
    private xrController1;
    private xrController2;
    private selectedXRController;
    private tracking;
    private frames;
    private initialized;
    private oldTarget;
    private placementComplete;
    private isTranslating;
    private isRotating;
    private isTwoHandInteraction;
    private lastDragPosition;
    private deltaRotation;
    private scaleLine;
    private firstRatio;
    private lastAngle;
    private goalPosition;
    private goalYaw;
    private goalScale;
    private xDamper;
    private yDamper;
    private zDamper;
    private yawDamper;
    private pitchDamper;
    private rollDamper;
    private scaleDamper;
    private wasTwoFingering;
    private worldSpaceInitialPlacementDone;
    private initialModelScale;
    private minScale;
    private maxScale;
    private onExitWebXRButtonContainerClick;
    /**
     * Check if world-space mode is active and initial placement is complete
     */
    private isWorldSpaceReady;
    constructor(renderer: Renderer);
    resolveARSession(): Promise<XRSession>;
    /**
     * The currently presented scene, if any
     */
    get presentedScene(): ModelScene | null;
    /**
     * Resolves to true if the renderer has detected all the necessary qualities
     * to support presentation in AR.
     */
    supportsPresentation(): Promise<boolean>;
    /**
     * Present a scene in AR
     */
    present(scene: ModelScene, environmentEstimation?: boolean): Promise<void>;
    private setupXRControllerLine;
    private setupController;
    private setupXRControllers;
    private hover;
    private controllerSeparation;
    private onControllerSelectStart;
    private onControllerSelectEnd;
    /**
     * If currently presenting a scene in AR, stops presentation and exits AR.
     */
    stopPresenting(): Promise<void>;
    /**
     * True if a scene is currently in the process of being presented in AR
     */
    get isPresenting(): boolean;
    get target(): Vector3;
    updateTarget(): void;
    onUpdateScene: () => void;
    private cleanupXRController;
    private postSessionCleanup;
    private updateView;
    private placeInitially;
    private getTouchLocation;
    private getHitPoint;
    moveToFloor(frame: XRFrame): void;
    private onSelectStart;
    private onSelectEnd;
    private fingerPolar;
    private setScale;
    private processInput;
    private applyXRControllerRotation;
    private handleScalingInXR;
    private updatePivotPosition;
    private updateYaw;
    private updateMenuPanel;
    private applyXRInputToScene;
    private updatePlacementBoxOpacity;
    private updateTwoHandInteractionState;
    private applyXRControllerRotations;
    private dispatchCameraChangeEvent;
    private updateXRControllerHover;
    /**
     * Enable user interaction for world-space mode after initial automatic
     * placement
     */
    private enableWorldSpaceUserInteraction;
    private handleFirstView;
    /**
     * Only public to make it testable.
     */
    onWebXRFrame(time: number, frame: XRFrame): void;
    /**
     * Calculate optimal scale and position for world-space AR presentation
     * Similar to the SVXR:FrameModel approach for consistent model presentation
     *
     * This method implements automatic model framing for world-space AR sessions:
     * 1. Calculates optimal viewing distance based on model size and minimum
     * distance
     * 2. Positions model at a drop angle below camera center for natural viewing
     * 3. Automatically scales model to fit within viewport constraints
     * 4. Ensures consistent presentation across different model sizes
     *
     * Note: This automatic placement only happens on the first session start.
     * After initial placement, users have full control over model position,
     * rotation, and scale.
     */
    private calculateWorldSpaceOptimalPlacement;
    /**
     * Calculate min/max scale for world-space AR, SVXR-style
     */
    private calculateWorldSpaceScaleLimits;
}
