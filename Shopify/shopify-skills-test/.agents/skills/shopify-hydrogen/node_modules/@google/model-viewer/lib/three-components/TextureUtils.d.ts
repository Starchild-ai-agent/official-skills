import { Texture, WebGLRenderer } from 'three';
export interface EnvironmentMapAndSkybox {
    environmentMap: Texture;
    skybox: Texture | null;
}
export default class TextureUtils {
    private threeRenderer;
    lottieLoaderUrl: string;
    private _ldrLoader;
    private _imageLoader;
    private _hdrLoader;
    private _lottieLoader;
    private generatedEnvironmentMap;
    private generatedEnvironmentMapAlt;
    private skyboxCache;
    private blurMaterial;
    private blurScene;
    constructor(threeRenderer: WebGLRenderer);
    private ldrLoader;
    private imageLoader;
    private hdrLoader;
    getLottieLoader(withCredentials: boolean): Promise<any>;
    loadImage(url: string, withCredentials: boolean): Promise<Texture>;
    loadLottie(url: string, quality: number, withCredentials: boolean): Promise<Texture>;
    loadEquirect(url: string, withCredentials?: boolean, progressCallback?: (progress: number) => void): Promise<Texture>;
    /**
     * Returns a { skybox, environmentMap } object with the targets/textures
     * accordingly. `skybox` is a WebGLRenderCubeTarget, and `environmentMap`
     * is a Texture from a WebGLRenderCubeTarget.
     */
    generateEnvironmentMapAndSkybox(skyboxUrl?: string | null, environmentMapUrl?: string | null, progressCallback?: (progress: number) => void, withCredentials?: boolean): Promise<EnvironmentMapAndSkybox>;
    /**
     * Loads an equirect Texture from a given URL, for use as a skybox.
     */
    private loadEquirectFromUrl;
    private GenerateEnvironmentMap;
    /**
     * Loads a dynamically generated environment map.
     */
    private loadGeneratedEnvironmentMap;
    /**
     * Loads a dynamically generated environment map, designed to be neutral and
     * color-preserving. Shows less contrast around the different sides of the
     * object.
     */
    private loadGeneratedEnvironmentMapAlt;
    private blurCubemap;
    private halfblur;
    private getBlurShader;
    dispose(): Promise<void>;
}
