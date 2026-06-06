/// <reference types="node" />
import { EventEmitter } from 'events';
import { OffscreenRenderEngine } from '../engines/offscreen-render-engine';
import { SeparatedInteractionsEngine } from '../engines/separated-interactions-engine';
export declare abstract class UIPlugin<S = {}> extends EventEmitter {
    name: string;
    abstract height?: number;
    interactionsEngine: SeparatedInteractionsEngine;
    renderEngine: OffscreenRenderEngine;
    min?: number;
    max?: number;
    styles?: S;
    protected constructor(name: string);
    init(renderEngine: OffscreenRenderEngine, interactionsEngine: SeparatedInteractionsEngine): void;
    postInit?(): void;
    render?(): boolean | undefined | void;
    setSettings?(settings: {
        styles: S;
    }): void;
    renderTooltip?(): boolean;
    postRender?(): void;
}
export default UIPlugin;
