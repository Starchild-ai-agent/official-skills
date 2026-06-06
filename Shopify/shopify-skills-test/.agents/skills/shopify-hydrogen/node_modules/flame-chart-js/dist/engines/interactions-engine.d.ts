/// <reference types="node" />
import { EventEmitter } from 'events';
import { RenderEngine } from './render-engine';
import { OffscreenRenderEngine } from './offscreen-render-engine';
import { CursorTypes, HitRegion, Mouse, RegionTypes } from '../types';
import { SeparatedInteractionsEngine } from './separated-interactions-engine';
export declare class InteractionsEngine extends EventEmitter {
    private renderEngine;
    private readonly canvas;
    private hitRegions;
    private instances;
    mouse: Mouse;
    selectedRegion: HitRegion | null;
    private hoveredRegion;
    private moveActive;
    private mouseDownPosition;
    private mouseDownHoveredInstance;
    private hoveredInstance;
    private currentCursor;
    constructor(canvas: HTMLCanvasElement, renderEngine: RenderEngine);
    makeInstance(renderEngine: OffscreenRenderEngine): SeparatedInteractionsEngine;
    reset(): void;
    destroy(): void;
    initListeners(): void;
    removeListeners(): void;
    handleMouseWheel(e: WheelEvent): void;
    handleMouseDown(): void;
    handleMouseUp(): void;
    handleMouseMove(e: MouseEvent): void;
    handleRegionHit(): void;
    checkRegionHover(): void;
    getHoveredRegion(): HitRegion<any>;
    clearHitRegions(): void;
    addHitRegion<T>(type: RegionTypes, data: T, x: number, y: number, w: number, h: number, cursor: CursorTypes): void;
    setCursor(cursor: string): void;
    clearCursor(): void;
}
