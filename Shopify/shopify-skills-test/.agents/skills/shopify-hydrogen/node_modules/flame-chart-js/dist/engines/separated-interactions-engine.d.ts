/// <reference types="node" />
import { EventEmitter } from 'events';
import { OffscreenRenderEngine } from './offscreen-render-engine';
import { CursorTypes, HitRegion, Mouse, RegionTypes } from '../types';
import { InteractionsEngine } from './interactions-engine';
export declare class SeparatedInteractionsEngine extends EventEmitter {
    static count: number;
    parent: InteractionsEngine;
    renderEngine: OffscreenRenderEngine;
    private readonly id;
    hitRegions: HitRegion[];
    static getId(): number;
    constructor(parent: InteractionsEngine, renderEngine: OffscreenRenderEngine);
    resend(event: string, ...args: [HitRegion, Mouse, boolean]): void;
    getMouse(): {
        x: number;
        y: number;
    };
    getGlobalMouse(): Mouse;
    clearHitRegions(): void;
    addHitRegion<T>(type: RegionTypes, data: T, x: number, y: number, w: number, h: number, cursor?: CursorTypes): void;
    setCursor(cursor: string): void;
    clearCursor(): void;
}
