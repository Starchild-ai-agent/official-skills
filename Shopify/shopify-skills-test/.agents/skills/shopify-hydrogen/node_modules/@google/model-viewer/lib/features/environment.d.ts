import ModelViewerElementBase from '../model-viewer-base.js';
import { Constructor } from '../utilities.js';
export declare const BASE_OPACITY = 0.5;
export type ToneMappingValue = 'auto' | 'aces' | 'agx' | 'commerce' | 'neutral' | 'reinhard' | 'cineon' | 'linear' | 'none';
export declare const $currentEnvironmentMap: unique symbol;
export declare const $currentBackground: unique symbol;
export declare const $updateEnvironment: unique symbol;
export declare interface EnvironmentInterface {
    environmentImage: string | null;
    skyboxImage: string | null;
    skyboxHeight: string;
    shadowIntensity: number;
    shadowSoftness: number;
    exposure: number;
    hasBakedShadow(): boolean;
}
export declare const EnvironmentMixin: <T extends Constructor<ModelViewerElementBase>>(ModelViewerElement: T) => Constructor<EnvironmentInterface> & T;
