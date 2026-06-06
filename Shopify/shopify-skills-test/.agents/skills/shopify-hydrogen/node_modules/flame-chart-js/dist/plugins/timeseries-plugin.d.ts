import { OffscreenRenderEngine } from '../engines/offscreen-render-engine';
import { SeparatedInteractionsEngine } from '../engines/separated-interactions-engine';
import { HitRegion, Timeseries, TimeseriesChart } from '../types';
import UIPlugin from './ui-plugin';
import { ChartStyle } from './utils/chart-render';
export type TimeseriesPluginStyles = {
    height: number;
};
export declare const defaultTimeseriesPluginStyles: TimeseriesPluginStyles;
export type TimeseriesPluginSettings = {
    styles?: Partial<TimeseriesPluginStyles>;
};
export type TimeseriesPreparedChart = TimeseriesChart & {
    group: string;
    style: ChartStyle;
};
export type PreparedTimeseries = {
    summary: Record<string, {
        min: number;
        max: number;
    }>;
    total: {
        min: number;
        max: number;
    };
    timeseries: TimeseriesPreparedChart[];
    timeboxes: {
        start: number;
        end: number;
    }[];
};
export declare class TimeseriesPlugin extends UIPlugin<TimeseriesPluginStyles> {
    height: number;
    private data;
    private hoveredRegion;
    constructor({ name, data, settings, }: {
        name?: string;
        data: Timeseries;
        settings?: TimeseriesPluginSettings;
    });
    init(renderEngine: OffscreenRenderEngine, interactionsEngine: SeparatedInteractionsEngine): void;
    handlePositionChange(position: {
        deltaX: number;
    }): void;
    handleMouseUp(): void;
    setSettings({ styles }?: TimeseriesPluginSettings): void;
    setData(data: Timeseries): void;
    handleHover(region: HitRegion<number> | null): void;
    renderTooltip(): boolean;
    render(): void;
}
