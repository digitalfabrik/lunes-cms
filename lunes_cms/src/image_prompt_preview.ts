// Live preview of the image generation prompt.
//
// The prompt is built on the server (services/image_generation.py), so the
// preview asks the server for it whenever the editor changes the additional
// info, the text option or the show-people toggle next to it. The inputs are
// looked up in the closest element marked with data-prompt-scope.
//
// A show-people toggle marked data-undecided belongs to a word that hasn't
// been classified yet. Its value isn't sent, so the server classifies the word
// and the answer sets the toggle.

type PromptPreviewResponse = {
    prompt?: string
    show_people?: boolean | null
}

const PREVIEW_DELAY_MS = 300

// Send the editor's show-people choice with a preview or generation request.
// Nothing is sent while the word is undecided, so the server decides.
// Also used by generate_image.ts and inline_regenerate.ts.
window.appendShowPeople = function (formData: FormData, toggle: HTMLInputElement | null): void {
    if (toggle && toggle.dataset.undecided === undefined) {
        formData.append("show_people", toggle.checked ? "true" : "false")
    }
}

function _initPromptPreview(info: HTMLElement): void {
    const previewUrl = info.dataset.previewUrl
    const preview = info.querySelector<HTMLElement>(".image-prompt-preview")
    const scope = info.closest<HTMLElement>("[data-prompt-scope]")
    if (!previewUrl || !preview || !scope) {
        return
    }
    const additionalInfo = scope.querySelector<HTMLInputElement>(".prompt-additional-info")
    const allowText = scope.querySelector<HTMLInputElement>(".prompt-allow-text")
    const showPeople = scope.querySelector<HTMLInputElement>(".prompt-show-people")

    let timer: number | undefined
    let latestRequest = 0

    const refresh = (): void => {
        const request = ++latestRequest
        const formData = new FormData()
        formData.append("additional_info", additionalInfo?.value ?? "")
        formData.append("allow_text_in_image", allowText?.checked ? "true" : "false")
        window.appendShowPeople(formData, showPeople)
        formData.append("csrfmiddlewaretoken", window.getCookie("csrftoken") ?? "")

        window
            .postWithCsrf(previewUrl, formData)
            .then(
                async (response) => (await window.readJsonBody(response)) as PromptPreviewResponse,
            )
            .then((data) => {
                // Ignore answers overtaken by a newer request.
                if (request !== latestRequest) {
                    return
                }
                if (data.prompt) {
                    preview.textContent = data.prompt
                }
                if (
                    showPeople &&
                    showPeople.dataset.undecided !== undefined &&
                    typeof data.show_people === "boolean"
                ) {
                    showPeople.checked = data.show_people
                    delete showPeople.dataset.undecided
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
    showPeople?.addEventListener("change", () => {
        delete showPeople.dataset.undecided
        scheduleRefresh()
    })
    if (showPeople?.dataset.undecided !== undefined) {
        refresh()
    }
}

document.addEventListener("DOMContentLoaded", () => {
    document
        .querySelectorAll<HTMLElement>(".image-prompt-info[data-preview-url]")
        .forEach((info) => _initPromptPreview(info))
})
