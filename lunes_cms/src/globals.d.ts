declare var $: JQueryStatic
declare var django: { jQuery: JQueryStatic }
declare function gettext(text: string): string

interface Window {
    getCookie: (name: string) => string | null
    assetManagerConfigs?: AssetManagerConfig[]
    audioAssetManagerConfig?: AudioAssetManagerConfig
    initAudioGenerator: (config: AudioGeneratorConfig) => void
    initImageGenerator: (config: ImageGeneratorConfig) => void
    document_overlay: (event: MouseEvent & { target: HTMLSelectElement }) => void
    renderReportsChart: (canvas: HTMLCanvasElement, data: ChartData) => void
}
