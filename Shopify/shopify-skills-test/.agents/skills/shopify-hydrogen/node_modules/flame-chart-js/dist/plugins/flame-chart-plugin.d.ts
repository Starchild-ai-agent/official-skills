import Color from 'color';
import UIPlugin from './ui-plugin';
import { ClusterizedFlatTree, ClusterizedFlatTreeNode, Colors, FlameChartNodes, FlatTree, FlatTreeNode, HitRegion, MetaClusterizedFlatTree } from '../types';
import { OffscreenRenderEngine } from '../engines/offscreen-render-engine';
import { SeparatedInteractionsEngine } from '../engines/separated-interactions-engine';
type ClusterNode = {
    data: FlatTreeNode;
    type: string;
};
declare const DEFAULT_COLOR: Color<string | number | Color<string | number | Color<string | number | Color<string | number | Color<string | number | Color<string | number | Color<string | number | Color<string | number | Color<string | number | Color<string | number | Color<string | number | Color<string | number | any | ArrayLike<number> | {
    [key: string]: any;
}> | ArrayLike<number> | {
    [key: string]: any;
}> | ArrayLike<number> | {
    [key: string]: any;
}> | ArrayLike<number> | {
    [key: string]: any;
}> | ArrayLike<number> | {
    [key: string]: any;
}> | ArrayLike<number> | {
    [key: string]: any;
}> | ArrayLike<number> | {
    [key: string]: any;
}> | ArrayLike<number> | {
    [key: string]: any;
}> | ArrayLike<number> | {
    [key: string]: any;
}> | ArrayLike<number> | {
    [key: string]: any;
}> | ArrayLike<number> | {
    [key: string]: any;
}> | ArrayLike<number> | {
    [key: string]: any;
}>;
export declare class FlameChartPlugin extends UIPlugin {
    height: number;
    data: FlameChartNodes;
    userColors: Colors;
    flatTree: FlatTree;
    positionY: number;
    colors: Colors;
    selectedRegion: ClusterNode | null;
    hoveredRegion: ClusterNode | null;
    lastRandomColor: typeof DEFAULT_COLOR;
    metaClusterizedFlatTree: MetaClusterizedFlatTree;
    actualClusterizedFlatTree: ClusterizedFlatTree;
    initialClusterizedFlatTree: ClusterizedFlatTree;
    lastUsedColor: string | null;
    renderChartTimeout: number;
    constructor({ data, colors, name, }: {
        data: FlameChartNodes;
        colors?: Colors;
        name?: string;
    });
    init(renderEngine: OffscreenRenderEngine, interactionsEngine: SeparatedInteractionsEngine): void;
    handlePositionChange({ deltaX, deltaY }: {
        deltaX: number;
        deltaY: number;
    }): void;
    handleMouseUp(): void;
    setPositionY(y: number): void;
    reset(): void;
    calcMinMax(): void;
    handleSelect(region: HitRegion<ClusterizedFlatTreeNode>): void;
    handleHover(region: HitRegion<ClusterizedFlatTreeNode>): void;
    findNodeInCluster(region: HitRegion<ClusterizedFlatTreeNode>): ClusterNode | null;
    getColor(type?: string, defaultColor?: string): string;
    setData(data: FlameChartNodes): void;
    parseData(): void;
    initData(): void;
    reclusterizeClusteredFlatTree(): void;
    calcRect(start: number, duration: number, level: number): {
        x: number;
        y: number;
        w: number;
    };
    renderTooltip(): boolean;
    render(): void;
}
export {};
