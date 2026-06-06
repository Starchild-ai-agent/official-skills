import ModelViewerElementBase from '../model-viewer-base.js';
import { Constructor } from '../utilities.js';
interface PlayAnimationOptions {
    repetitions: number;
    pingpong: boolean;
}
interface AppendAnimationOptions {
    pingpong: boolean;
    repetitions: number | null;
    weight: number;
    timeScale: number;
    fade: boolean | number;
    warp: boolean | number;
    relativeWarp: boolean;
    time: number | null;
}
interface DetachAnimationOptions {
    fade: boolean | number;
}
export declare interface AnimationInterface {
    autoplay: boolean;
    animationName: string | void;
    animationCrossfadeDuration: number;
    readonly availableAnimations: Array<string>;
    readonly paused: boolean;
    readonly duration: number;
    currentTime: number;
    timeScale: number;
    pause(): void;
    play(options?: PlayAnimationOptions): void;
    appendAnimation(animationName: string, options?: AppendAnimationOptions): void;
    detachAnimation(animationName: string, options?: DetachAnimationOptions): void;
}
export declare const AnimationMixin: <T extends Constructor<ModelViewerElementBase>>(ModelViewerElement: T) => Constructor<AnimationInterface> & T;
export {};
