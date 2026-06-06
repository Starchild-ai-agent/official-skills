import ModelViewerElementBase from '../model-viewer-base.js';
import { ARStatus, ARTracking } from '../three-components/ARRenderer.js';
import { Constructor } from '../utilities.js';
export type ARMode = 'quick-look' | 'scene-viewer' | 'webxr' | 'none';
export interface ARStatusDetails {
    status: ARStatus;
}
export interface ARTrackingDetails {
    status: ARTracking;
}
export declare const $openSceneViewer: unique symbol;
export declare const $openIOSARQuickLook: unique symbol;
export declare interface ARInterface {
    ar: boolean;
    arModes: string;
    arScale: string;
    arPlacement: string;
    iosSrc: string | null;
    xrEnvironment: boolean;
    arUsdzMaxTextureSize: string;
    readonly canActivateAR: boolean;
    activateAR(): Promise<void>;
}
export declare const ARMixin: <T extends Constructor<ModelViewerElementBase>>(ModelViewerElement: T) => Constructor<ARInterface> & T;
