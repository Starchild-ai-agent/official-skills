/// <reference types="node" />
import { RenderEngine } from './engines/render-engine';
import { InteractionsEngine } from './engines/interactions-engine';
import { EventEmitter } from 'events';
import { TimeGrid, TimeGridStyles } from './engines/time-grid';
import { RenderOptions, RenderStyles } from './engines/basic-render-engine';
import UIPlugin from './plugins/ui-plugin';
export type FlameChartContainerStyles<Styles = {}> = {
    timeGrid?: Partial<TimeGridStyles>;
    main?: Partial<RenderStyles>;
} & Styles;
export interface FlameChartContainerSettings<Styles = {}> {
    options?: Partial<RenderOptions>;
    styles?: FlameChartContainerStyles<Styles>;
}
export interface FlameChartContainerOptions<Styles = {}> {
    canvas: HTMLCanvasElement;
    plugins: UIPlugin[];
    settings?: FlameChartContainerSettings<Styles>;
}
export declare class FlameChartContainer<Styles = {}> extends EventEmitter {
    renderEngine: RenderEngine;
    interactionsEngine: InteractionsEngine;
    plugins: UIPlugin[];
    timeGrid: TimeGrid;
    constructor({ canvas, plugins, settings }: FlameChartContainerOptions<Styles>);
    render(): void;
    resize(width: number, height: number): void;
    execOnPlugins(fnName: string, ...args: any[]): void;
    setSettings(settings: FlameChartContainerSettings<Styles>): void;
    setZoom(start: number, end: number): void;
}
export default FlameChartContainer;
