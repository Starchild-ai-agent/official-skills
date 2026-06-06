import { OffscreenRenderEngine } from '../engines/offscreen-render-engine';
import UIPlugin from './ui-plugin';
import { SeparatedInteractionsEngine } from '../engines/separated-interactions-engine';
export type TimeGridPluginStyles = {
    font: string;
    fontColor: string;
};
export type TimeGridPluginSettings = {
    styles?: Partial<TimeGridPluginStyles>;
};
export declare const defaultTimeGridPluginStyles: TimeGridPluginStyles;
export declare class TimeGridPlugin extends UIPlugin<TimeGridPluginStyles> {
    styles: TimeGridPluginStyles;
    height: number;
    constructor(settings?: TimeGridPluginSettings);
    setSettings({ styles }: TimeGridPluginSettings): void;
    overrideEngineSettings(): void;
    init(renderEngine: OffscreenRenderEngine, interactionsEngine: SeparatedInteractionsEngine): void;
    render(): boolean;
}
