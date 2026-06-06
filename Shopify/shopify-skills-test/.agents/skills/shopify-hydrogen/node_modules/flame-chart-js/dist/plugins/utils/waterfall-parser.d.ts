import { Waterfall, WaterfallItem, WaterfallItemMeta } from '../../types';
export type PreparedWaterfallInterval = {
    start: number;
    end: number;
    color: string;
    type: 'block' | 'line';
    name: string;
};
export type PreparedWaterfallTextBlock = {
    start: number;
    end: number;
};
export type PreparedWaterfallItem = {
    intervals: PreparedWaterfallInterval[];
    textBlock: PreparedWaterfallTextBlock;
    timing: WaterfallItem['timing'];
    name: string;
    min: number;
    max: number;
    index: number;
    meta?: WaterfallItemMeta[];
};
export declare const parseWaterfall: (waterfall: Waterfall) => PreparedWaterfallItem[];
