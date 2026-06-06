import { TimeGrid } from './time-grid';
import { BasicRenderEngine, RenderSettings } from './basic-render-engine';
import { OffscreenRenderEngine } from './offscreen-render-engine';
import UIPlugin from '../plugins/ui-plugin';
export type RenderEngineArgs = {
    canvas: HTMLCanvasElement;
    settings: RenderSettings;
    timeGrid: TimeGrid;
    plugins: UIPlugin[];
};
export declare class RenderEngine extends BasicRenderEngine {
    plugins: UIPlugin[];
    children: OffscreenRenderEngine[];
    requestedRenders: number[];
    timeGrid: TimeGrid;
    freeSpace: number;
    lastPartialAnimationFrame: number | null;
    lastGlobalAnimationFrame: number | null;
    constructor({ canvas, settings, timeGrid, plugins }: RenderEngineArgs);
    makeInstance(): OffscreenRenderEngine;
    calcMinMax(): void;
    calcTimeGrid(): void;
    setMinMax(min: number, max: number): void;
    setSettings(data: RenderSettings): void;
    resize(width: number, height: number): boolean;
    recalcChildrenSizes(): void;
    getChildrenSizes(): {
        width: number;
        position: number;
        height: number;
    }[];
    getAccuracy(): number;
    setZoom(zoom: number): boolean;
    setPositionX(x: number): number;
    renderPlugin(index: number): void;
    partialRender(id?: number): void;
    shallowRender(): void;
    render(prepare?: () => void): void;
}
