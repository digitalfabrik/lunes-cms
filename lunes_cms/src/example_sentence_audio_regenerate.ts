"use strict"

// (Re)generation of a word's example sentence audio in the admin list view:
// the generate button creates a temporary audio file via OpenAI and shows it
// next to the keep/discard buttons, so it can be listened to before it
// replaces the current audio.

type SentenceAudioRegenPanel = {
    button: HTMLButtonElement
    panel: HTMLElement
    player: HTMLAudioElement
}

function _findSentenceAudioRegenPanel(el: HTMLElement): SentenceAudioRegenPanel | null {
    const container = el.closest<HTMLElement>(".word-example-sentence-audio-container")
    const button = container?.querySelector<HTMLButtonElement>(
        ".regenerate-example-sentence-audio-btn",
    )
    const panel = container?.querySelector<HTMLElement>(".example-sentence-audio-regen")
    const player = panel?.querySelector<HTMLAudioElement>(".example-sentence-audio-regen-player")
    if (!button || !panel || !player) {
        return null
    }
    return { button, panel, player }
}

function _sentenceAudioErrorText(error: unknown): string {
    return `${gettext("Error")}: ${error instanceof Error ? error.message : String(error)}`
}

function _generateSentenceAudio(regen: SentenceAudioRegenPanel): void {
    const { button, panel, player } = regen
    const generateUrl = button.dataset.generateUrl
    if (!generateUrl) {
        return
    }

    const formData = new FormData()
    formData.append("example_sentence_text", button.dataset.text ?? "")

    button.disabled = true
    window
        .postWithCsrf(generateUrl, formData)
        .then(async (response) => {
            const data = await window.readJsonBody(response)
            const url = data.temp_audio_url
            const filename = data.temp_audio_filename
            if (!response.ok || typeof url !== "string" || typeof filename !== "string") {
                throw new Error(
                    data.error ?? data.message ?? `HTTP error! status: ${response.status}`,
                )
            }
            player.src = url
            panel.dataset.tempAudioFilename = filename
            panel.style.display = "block"
        })
        .catch((error: unknown) => {
            alert(_sentenceAudioErrorText(error))
        })
        .finally(() => {
            button.disabled = false
        })
}

function _keepSentenceAudio(regen: SentenceAudioRegenPanel, keepButton: HTMLButtonElement): void {
    const storeUrl = regen.button.dataset.storeUrl
    const filename = regen.panel.dataset.tempAudioFilename
    if (!storeUrl || !filename) {
        return
    }

    const formData = new FormData()
    formData.append("temp_audio_filename", filename)

    keepButton.disabled = true
    // The store endpoint only answers with JSON for AJAX requests.
    fetch(storeUrl, {
        method: "POST",
        body: formData,
        credentials: "same-origin",
        headers: {
            "X-CSRFToken": window.getCookie("csrftoken") ?? "",
            "X-Requested-With": "XMLHttpRequest",
        },
    })
        .then(async (response) => {
            const data = await window.readJsonBody(response)
            if (!response.ok || data.status !== "success") {
                throw new Error(data.message ?? `HTTP error! status: ${response.status}`)
            }
            // Reload so the reset check status and the new player are shown.
            window.location.reload()
        })
        .catch((error: unknown) => {
            keepButton.disabled = false
            alert(_sentenceAudioErrorText(error))
        })
}

function _discardSentenceAudio(regen: SentenceAudioRegenPanel): void {
    regen.player.pause()
    regen.player.removeAttribute("src")
    delete regen.panel.dataset.tempAudioFilename
    regen.panel.style.display = "none"
}

document.addEventListener("DOMContentLoaded", () => {
    document.addEventListener("click", (event) => {
        const target = event.target as HTMLElement

        const button = target.closest<HTMLButtonElement>(
            ".regenerate-example-sentence-audio-btn, .keep-example-sentence-audio-btn, .discard-example-sentence-audio-btn",
        )
        const regen = button ? _findSentenceAudioRegenPanel(button) : null
        if (!button || !regen) {
            return
        }
        event.preventDefault()

        if (button.classList.contains("regenerate-example-sentence-audio-btn")) {
            _generateSentenceAudio(regen)
        } else if (button.classList.contains("keep-example-sentence-audio-btn")) {
            _keepSentenceAudio(regen, button)
        } else {
            _discardSentenceAudio(regen)
        }
    })
})
