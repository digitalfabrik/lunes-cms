"use strict"

// Inline example sentence generation with a keep/discard step, mirroring the
// audio and image widgets: generate a sentence for review, then either keep it
// (persisted right away) or discard it, without leaving the change page.

function _getSentenceCookie(name: string): string | null {
    let cookieValue = null
    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";")
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim()
            if (cookie.substring(0, name.length + 1) === name + "=") {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1))
                break
            }
        }
    }
    return cookieValue
}

function _findSentenceTextarea(button: HTMLButtonElement): HTMLTextAreaElement | null {
    if (button.dataset.target) {
        return document.getElementById(button.dataset.target) as HTMLTextAreaElement | null
    }
    // Inline rows: the textarea lives in a sibling cell of the same row.
    const row = button.closest("tr")
    return row?.querySelector<HTMLTextAreaElement>('textarea[name$="-example_sentence"]') ?? null
}

type SentenceWidget = {
    container: HTMLElement
    generateButton: HTMLButtonElement
    spinner: HTMLElement | null
    messageArea: HTMLElement | null
    decision: HTMLElement | null
    preview: HTMLElement | null
    keepButton: HTMLButtonElement | null
    discardButton: HTMLButtonElement | null
    textarea: HTMLTextAreaElement | null
}

function _resolveWidget(button: HTMLElement): SentenceWidget | null {
    const container = button.closest<HTMLElement>(".generate-example-sentence")
    if (!container) {
        return null
    }
    const generateButton = container.querySelector<HTMLButtonElement>(
        ".generate-example-sentence-btn",
    )
    if (!generateButton) {
        return null
    }
    return {
        container,
        generateButton,
        spinner: container.querySelector<HTMLElement>(".generate-example-sentence-spinner"),
        messageArea: container.querySelector<HTMLElement>(".generate-example-sentence-message"),
        decision: container.querySelector<HTMLElement>(".generate-example-sentence-decision"),
        preview: container.querySelector<HTMLElement>(".generate-example-sentence-preview"),
        keepButton: container.querySelector<HTMLButtonElement>(
            ".generate-example-sentence-keep-btn",
        ),
        discardButton: container.querySelector<HTMLButtonElement>(
            ".generate-example-sentence-discard-btn",
        ),
        textarea: _findSentenceTextarea(generateButton),
    }
}

function _showMessage(widget: SentenceWidget, text: string, color: string): void {
    if (widget.messageArea) {
        widget.messageArea.textContent = text
        widget.messageArea.style.color = color
    }
}

function _setDecisionDisabled(widget: SentenceWidget, disabled: boolean): void {
    if (widget.keepButton) {
        widget.keepButton.disabled = disabled
    }
    if (widget.discardButton) {
        widget.discardButton.disabled = disabled
    }
}

function _hideDecision(widget: SentenceWidget): void {
    if (widget.decision) {
        widget.decision.style.display = "none"
    }
    if (widget.preview) {
        widget.preview.textContent = ""
    }
    delete widget.container.dataset.pendingSentence
}

function _handleGenerate(button: HTMLButtonElement): void {
    const widget = _resolveWidget(button)
    if (!widget || !button.dataset.url) {
        return
    }

    if (!widget.textarea) {
        _showMessage(widget, gettext("Could not find the example sentence field."), "red")
        return
    }

    button.disabled = true
    if (widget.spinner) {
        widget.spinner.style.display = "inline-block"
    }
    _hideDecision(widget)
    _showMessage(widget, gettext("Generating example sentence..."), "inherit")

    fetch(button.dataset.url, {
        method: "POST",
        credentials: "same-origin",
        headers: {
            "X-CSRFToken": _getSentenceCookie("csrftoken") ?? "",
        },
    })
        .then(async (response) => {
            const data = (await response.json()) as {
                message?: string
                example_sentence?: string
                error?: string
            }
            if (!response.ok || data.error || !data.example_sentence) {
                throw new Error(data.error ?? `HTTP error! status: ${response.status}`)
            }
            return data
        })
        .then((data) => {
            const sentence = data.example_sentence ?? ""
            widget.container.dataset.pendingSentence = sentence
            if (widget.preview) {
                widget.preview.textContent = sentence
            }
            if (widget.decision) {
                widget.decision.style.display = ""
            }
            _setDecisionDisabled(widget, false)
            button.textContent =
                button.dataset.regenerateLabel ?? gettext("Regenerate example sentence")
            _showMessage(widget, data.message ?? gettext("Example sentence generated!"), "green")
        })
        .catch((error: unknown) => {
            _hideDecision(widget)
            _showMessage(
                widget,
                `${gettext("Error")}: ${error instanceof Error ? error.message : String(error)}`,
                "red",
            )
        })
        .finally(() => {
            button.disabled = false
            if (widget.spinner) {
                widget.spinner.style.display = "none"
            }
        })
}

function _handleKeep(button: HTMLButtonElement): void {
    const widget = _resolveWidget(button)
    if (!widget) {
        return
    }

    const sentence = widget.container.dataset.pendingSentence ?? ""
    const storeUrl = widget.generateButton.dataset.storeUrl

    if (widget.textarea) {
        widget.textarea.value = sentence
        widget.textarea.dispatchEvent(new Event("change", { bubbles: true }))
    }

    // Without a store endpoint, fall back to filling the field for a manual save.
    if (!storeUrl) {
        _hideDecision(widget)
        return
    }

    _setDecisionDisabled(widget, true)
    _showMessage(widget, gettext("Saving..."), "inherit")

    const formData = new FormData()
    formData.append("example_sentence", sentence)
    formData.append("csrfmiddlewaretoken", _getSentenceCookie("csrftoken") ?? "")

    fetch(storeUrl, {
        method: "POST",
        body: formData,
        credentials: "same-origin",
        headers: {
            "X-CSRFToken": _getSentenceCookie("csrftoken") ?? "",
            "X-Requested-With": "XMLHttpRequest",
        },
    })
        .then(async (response) => {
            const data = (await response.json()) as { status?: string; message?: string }
            if (!response.ok || data.status !== "success") {
                throw new Error(data.message ?? `HTTP error! status: ${response.status}`)
            }
            return data
        })
        .then(() => {
            // Reload so the reset check status and cleared audio are reflected.
            window.location.reload()
        })
        .catch((error: unknown) => {
            _setDecisionDisabled(widget, false)
            _showMessage(
                widget,
                `${gettext("Error")}: ${error instanceof Error ? error.message : String(error)}`,
                "red",
            )
        })
}

function _handleDiscard(button: HTMLButtonElement): void {
    const widget = _resolveWidget(button)
    if (!widget) {
        return
    }
    _hideDecision(widget)
    widget.generateButton.textContent =
        widget.generateButton.dataset.generateLabel ?? gettext("Generate example sentence")
    _showMessage(widget, "", "inherit")
}

document.addEventListener("DOMContentLoaded", () => {
    document.addEventListener("click", (event) => {
        const target = event.target as HTMLElement

        const generateButton = target.closest<HTMLButtonElement>(".generate-example-sentence-btn")
        if (generateButton?.dataset.url) {
            event.preventDefault()
            _handleGenerate(generateButton)
            return
        }

        const keepButton = target.closest<HTMLButtonElement>(".generate-example-sentence-keep-btn")
        if (keepButton) {
            event.preventDefault()
            _handleKeep(keepButton)
            return
        }

        const discardButton = target.closest<HTMLButtonElement>(
            ".generate-example-sentence-discard-btn",
        )
        if (discardButton) {
            event.preventDefault()
            _handleDiscard(discardButton)
        }
    })
})
