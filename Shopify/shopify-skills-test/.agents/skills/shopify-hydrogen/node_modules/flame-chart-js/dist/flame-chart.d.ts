import { FlameChartContainer, FlameChartContainerSettings } from './flame-chart-container';
import { TimeGridPluginStyles } from './plugins/time-grid-plugin';
import { TimeframeSelectorPluginStyles } from './plugins/timeframe-selector-plugin';
import { WaterfallPluginStyles } from './plugins/waterfall-plugin';
import { TogglePluginStyles } from './plugins/toggle-plugin';
import { Colors, FlameChartNodes, Marks, Timeseries, Waterfall } from './types';
import { UIPlugin } from './plugins/ui-plugin';
import { TimeseriesPluginStyles } from './plugins/timeseries-plugin';
export type FlameChartStyles = {
    timeGridPlugin?: Partial<TimeGridPluginStyles>;
    timeframeSelectorPlugin?: Partial<TimeframeSelectorPluginStyles>;
    waterfallPlugin?: Partial<WaterfallPluginStyles>;
    togglePlugin?: Partial<TogglePluginStyles>;
    timeseriesPlugin?: Partial<TimeseriesPluginStyles>;
};
export type FlameChartSettings = {
    headers?: Partial<{
        waterfall: string;
        flameChart: string;
    }>;
} & FlameChartContainerSettings<FlameChartStyles>;
export type FlameChartOptions = {
    canvas: HTMLCanvasElement;
    data?: FlameChartNodes;
    marks?: Marks;
    waterfall?: Waterfall;
    timeframeTimeseries?: Timeseries;
    timeseries?: Timeseries;
    colors?: Colors;
    settings?: FlameChartSettings;
    plugins?: UIPlugin[];
};
export declare class FlameChart extends FlameChartContainer<FlameChartStyles> {
    setNodes: (nodes: FlameChartNodes) => void;
    setTimeseries: (timeseries: Timeseries) => void;
    setTimeframeTimeseries: (timeseries: Timeseries) => void;
    setMarks: (data: Marks) => void;
    setWaterfall: (data: Waterfall) => void;
    setFlameChartPosition: ({ x, y }: {
        x?: number;
        y?: number;
    }) => void;
    constructor({ canvas, data, marks, waterfall, timeframeTimeseries, timeseries, colors, settings, plugins, }: FlameChartOptions);
}
export default FlameChart;
