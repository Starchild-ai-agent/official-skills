import ModelViewerElementBase from '../model-viewer-base.js';
export type Constructor<T = object> = {
    new (...args: any[]): T;
};
export declare const BasicSpecTemplate: (ModelViewerElementAccessor: () => Constructor<ModelViewerElementBase>, tagNameAccessor: () => string) => void;
