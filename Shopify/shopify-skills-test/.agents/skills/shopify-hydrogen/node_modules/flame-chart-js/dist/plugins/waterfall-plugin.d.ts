import UIPlugin from './ui-plugin';
import { HitRegion, Waterfall, WaterfallItems } from '../types';
import { OffscreenRenderEngine } from '../engines/offscreen-render-engine';
import { SeparatedInteractionsEngine } from '../engines/separated-interactions-engine';
import { PreparedWaterfallItem } from './utils/waterfall-parser';
export type WaterfallPluginStyles = {
    defaultHeight: number;
};
export type WaterfallPluginSettings = {
    styles?: Partial<WaterfallPluginStyles>;
};
export declare const defaultWaterfallPluginStyles: WaterfallPluginStyles;
export declare class WaterfallPlugin extends UIPlugin<WaterfallPluginStyles> {
    styles: WaterfallPluginStyles;
    height: number;
    data: PreparedWaterfallItem[];
    positionY: number;
    hoveredRegion: HitRegion<number> | null;
    selectedRegion: HitRegion<number> | null;
    initialData: WaterfallItems;
    constructor({ data, name, settings, }: {
        name?: string;
        data: Waterfall;
        settings: WaterfallPluginSettings;
    });
    init(renderEngine: OffscreenRenderEngine, interactionsEngine: SeparatedInteractionsEngine): void;
    handlePositionChange({ deltaX, deltaY }: {
        deltaX: number;
        deltaY: number;
    }): void;
    handleMouseUp(): void;
    handleHover(region: HitRegion<number> | null): void;
    handleSelect(region: HitRegion<number> | null): void;
    setPositionY(y: number): void;
    setSettings({ styles }: WaterfallPluginSettings): void;
    setData(waterfall: Waterfall): void;
    calcRect(start: number, duration: number, isEnd: boolean): {
        x: number;
        w: number;
    };
    renderTooltip(): boolean;
    render(): void;
}
