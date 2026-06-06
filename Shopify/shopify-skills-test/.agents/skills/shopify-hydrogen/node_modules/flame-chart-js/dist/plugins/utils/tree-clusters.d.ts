import { ClusterizedFlatTree, MetaClusterizedFlatTree, FlameChartNodes, FlatTree, FlatTreeNode, FlameChartNode } from '../../types';
export declare const walk: (treeList: FlameChartNodes, cb: (child: FlameChartNode, parent: any, level: number) => FlatTreeNode, parent?: FlatTreeNode | FlameChartNode | null, level?: number) => void;
export declare const flatTree: (treeList: FlameChartNodes) => FlatTree;
export declare const getFlatTreeMinMax: (flatTree: FlatTree) => {
    min: number;
    max: number;
};
export declare function metaClusterizeFlatTree(flatTree: FlatTree, condition?: (prevNode: FlatTreeNode, node: FlatTreeNode) => boolean): MetaClusterizedFlatTree;
export declare const clusterizeFlatTree: (metaClusterizedFlatTree: MetaClusterizedFlatTree, zoom: number, start?: number, end?: number, stickDistance?: number, minBlockSize?: number) => ClusterizedFlatTree;
export declare const reclusterizeClusteredFlatTree: (clusteredFlatTree: ClusterizedFlatTree, zoom: number, start: number, end: number, stickDistance?: number, minBlockSize?: number) => ClusterizedFlatTree;
