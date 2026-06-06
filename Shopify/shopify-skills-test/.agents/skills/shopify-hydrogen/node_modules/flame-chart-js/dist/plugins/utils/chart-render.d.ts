import { RenderEngine } from '../../engines/render-engine';
import { OffscreenRenderEngine } from '../../engines/offscreen-render-engine';
import { Timeseries, TimeseriesChart, TooltipField } from '../../types';
import { PreparedTimeseries } from '../timeseries-plugin';
export type ChartPoint = [number, number];
export type ChartPoints = ChartPoint[];
export type ChartLineType = 'smooth' | 'bar' | 'line';
export type ChartStyle = {
    fillColor: string;
    lineWidth: number;
    lineDash: number[];
    lineColor: string;
    type: ChartLineType;
};
export declare const defaultChartStyle: ChartStyle;
export declare const prepareTmeseries: (timeseries: Timeseries) => PreparedTimeseries;
export declare const getMinMax: (points: ChartPoints, chart: TimeseriesChart, summary: Record<string, {
    min: number;
    max: number;
}>) => {
    min: number;
    max: number;
};
export declare const renderChartTooltipFields: (timestamp: number, { timeseries }: PreparedTimeseries) => TooltipField[];
export declare const renderChart: ({ engine, points, style, min, max, }: {
    engine: RenderEngine | OffscreenRenderEngine;
    points: ChartPoints;
    min: number;
    max: number;
    style?: Partial<ChartStyle>;
}) => void;
export declare const chartPointsBinarySearch: (array: ChartPoints, value: number, outside?: boolean) => ChartPoint | null;
