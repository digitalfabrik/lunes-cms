// Live preview of the image generation prompt.
//
// The prompt is built on the server (services/image_generation.py), so the
// preview asks the server for it whenever the editor changes the additional
// info or the text option next to it. The inputs are looked up in the closest
// element marked with data-prompt-scope.

type PromptPreviewResponse = {
    prompt?: string
}

const PREVIEW_DELAY_MS = 300

function _initPromptPreview(info: HTMLElement): void {
    const previewUrl = info.dataset.previewUrl
    const preview = info.querySelector<HTMLElement>(".image-prompt-preview")
    const scope = info.closest<HTMLElement>("[data-prompt-scope]")
    if (!previewUrl || !preview || !scope) {
        return
    }
    const additionalInfo = scope.querySelector<HTMLInputElement>(".prompt-additional-info")
    const allowText = scope.querySelector<HTMLInputElement>(".prompt-allow-text")

    let timer: number | undefined
    let latestRequest = 0

    const refresh = (): void => {
        const request = ++latestRequest
        const formData = new FormData()
        formData.append("additional_info", additionalInfo?.value ?? "")
        formData.append("allow_text_in_image", allowText?.checked ? "true" : "false")
        formData.append("csrfmiddlewaretoken", window.getCookie("csrftoken") ?? "")

        window
            .postWithCsrf(previewUrl, formData)
            .then(
                async (response) => (await window.readJsonBody(response)) as PromptPreviewResponse,
            )
            .then((data) => {
                // Ignore answers overtaken by a newer request.
                if (request === latestRequest && data.prompt) {
                    preview.textContent = data.prompt
                }
            })
            .catch(() => {
                // Keep showing the last known prompt.
            })
            .finally(() => {
                if (request === latestRequest) {
                    preview.classList.remove("is-stale")
                }
            })
    }

    const scheduleRefresh = (): void => {
        preview.classList.add("is-stale")
        window.clearTimeout(timer)
        timer = window.setTimeout(refresh, PREVIEW_DELAY_MS)
    }

    additionalInfo?.addEventListener("input", scheduleRefresh)
    allowText?.addEventListener("change", scheduleRefresh)
}

document.addEventListener("DOMContentLoaded", () => {
    document
        .querySelectorAll<HTMLElement>(".image-prompt-info[data-preview-url]")
        .forEach((info) => _initPromptPreview(info))
})
