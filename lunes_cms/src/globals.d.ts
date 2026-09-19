declare var $: JQueryStatic
declare var django: { jQuery: JQueryStatic }
declare function gettext(text: string): string

interface JsonBody {
    status?: string
    message?: string
    error?: string
    [key: string]: unknown
}

interface Window {
    getCookie: (name: string) => string | null
    postWithCsrf: (url: string, body?: FormData) => Promise<Response>
    readJsonBody: (response: Response) => Promise<JsonBody>
    assetManagerConfigs?: AssetManagerConfig[]
    audioAssetManagerConfig?: AudioAssetManagerConfig
    initAudioGenerator: (config: AudioGeneratorConfig) => void
    initImageGenerator: (config: ImageGeneratorConfig) => void
    document_overlay: (event: MouseEvent & { target: HTMLSelectElement }) => void
    renderReportsChart: (canvas: HTMLCanvasElement, data: ChartData) => void
}
