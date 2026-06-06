import UIPlugin from './ui-plugin';
import { HitRegion, Mark, Marks } from '../types';
import { OffscreenRenderEngine } from '../engines/offscreen-render-engine';
import { SeparatedInteractionsEngine } from '../engines/separated-interactions-engine';
type MarkHitRegion = HitRegion<Mark>;
export declare class MarksPlugin extends UIPlugin {
    marks: Marks;
    hoveredRegion: MarkHitRegion | null;
    selectedRegion: MarkHitRegion | null;
    constructor({ data, name }: {
        data: Marks;
        name?: string;
    });
    calcMinMax(): void;
    init(renderEngine: OffscreenRenderEngine, interactionsEngine: SeparatedInteractionsEngine): void;
    handleHover(region: MarkHitRegion): void;
    handleSelect(region: MarkHitRegion): void;
    get height(): number;
    prepareMarks(marks: Marks): {
        color: string;
        shortName: string;
        fullName: string;
        timestamp: number;
    }[];
    setMarks(marks: Marks): void;
    calcMarksBlockPosition(position: number, prevEnding: number): number;
    render(): void;
    postRender(): void;
    renderTooltip(): boolean;
}
export {};
