import { SeparatedInteractionsEngine } from '../engines/separated-interactions-engine';
import { OffscreenRenderEngine } from '../engines/offscreen-render-engine';
import UIPlugin from './ui-plugin';
export type TogglePluginStyles = {
    height: number;
    color: string;
    strokeColor: string;
    dotsColor: string;
    fontColor: string;
    font: string;
    triangleWidth: number;
    triangleHeight: number;
    triangleColor: string;
    leftPadding: number;
};
export type TogglePluginSettings = {
    styles?: Partial<TogglePluginStyles>;
};
export declare const defaultTogglePluginStyles: TogglePluginStyles;
export declare class TogglePlugin extends UIPlugin<TogglePluginStyles> {
    styles: TogglePluginStyles;
    height: number;
    title: string;
    resizeActive: boolean;
    resizeStartHeight: number;
    resizeStartPosition: number;
    constructor(title: string, settings?: TogglePluginSettings);
    setSettings({ styles }?: TogglePluginSettings): void;
    init(renderEngine: OffscreenRenderEngine, interactionsEngine: SeparatedInteractionsEngine): void;
    getPrevEngine(): OffscreenRenderEngine;
    getNextEngine(): OffscreenRenderEngine;
    render(): void;
}
