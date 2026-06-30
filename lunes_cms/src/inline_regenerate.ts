// Inline (re)generation widget for the word detail page.
//
// Each widget lets a user generate a new audio file or image via OpenAI right
// on the change page, compare it side by side with the current one, and then
// either keep the new version or discard it and keep the current one.
//
// The widget is fully described by data attributes on its container, so the
// same code drives word audio, word image and example sentence audio.

type RegenerateResponse = {
    message?: string
    error?: string
    temp_audio_url?: string
    temp_audio_filename?: string
    temp_image_url?: string
    temp_image_filename?: string
}

function _initRegenerateWidget(widget: HTMLElement): void {
    const assetType = widget.dataset.assetType ?? "audio"
    const generateUrl = widget.dataset.generateUrl
    const storeUrl = widget.dataset.storeUrl
    const textField = widget.dataset.textField
    const textValue = widget.dataset.text ?? ""
    const storeField = widget.dataset.storeField ?? "temp_audio_filename"

    if (!generateUrl || !storeUrl || !textField) {
        return
    }

    const generateButton = widget.querySelector<HTMLButtonElement>(".regen-generate-btn")
    const keepButton = widget.querySelector<HTMLButtonElement>(".regen-keep-btn")
    const discardButton = widget.querySelector<HTMLButtonElement>(".regen-discard-btn")
    const spinner = widget.querySelector<HTMLElement>(".regen-spinner")
    const messageArea = widget.querySelector<HTMLElement>(".regen-message")
    const newEmpty = widget.querySelector<HTMLElement>(".regen-new-empty")
    const newPreview = widget.querySelector<HTMLElement>(".regen-new-preview")
    const decision = widget.querySelector<HTMLElement>(".regen-decision")
    const additionalInfo = widget.querySelector<HTMLInputElement>(".regen-additional-info")

    if (!generateButton || !keepButton || !discardButton || !newEmpty || !newPreview || !decision) {
        return
    }

    const generateLabel = generateButton.textContent ?? gettext("Generate")
    const regenerateLabel = generateButton.dataset.regenerateLabel ?? gettext("Regenerate")

    let tempFilename: string | null = null

    const showMessage = (text: string, state: "" | "success" | "error"): void => {
        if (messageArea) {
            messageArea.textContent = text
            messageArea.classList.remove("regen-message-success", "regen-message-error")
            if (state) {
                messageArea.classList.add(`regen-message-${state}`)
            }
        }
    }

    const setBusy = (busy: boolean): void => {
        generateButton.disabled = busy
        keepButton.disabled = busy
        discardButton.disabled = busy
        if (spinner) {
            spinner.classList.toggle("is-hidden", !busy)
        }
    }

    const clearNew = (): void => {
        tempFilename = null
        newPreview.innerHTML = ""
        newEmpty.classList.remove("is-hidden")
        decision.classList.add("is-hidden")
    }

    const renderNewPreview = (url: string): void => {
        newPreview.innerHTML = ""
        if (assetType === "image") {
            const img = document.createElement("img")
            img.src = url
            img.alt = gettext("Newly generated image")
            newPreview.appendChild(img)
        } else {
            const audio = document.createElement("audio")
            audio.controls = true
            audio.src = url
            newPreview.appendChild(audio)
        }
    }

    generateButton.addEventListener("click", () => {
        setBusy(true)
        showMessage(gettext("Generating..."), "")

        const formData = new FormData()
        formData.append(textField, textValue)
        if (assetType === "image" && additionalInfo) {
            formData.append("additional_info", additionalInfo.value)
        }
        formData.append("csrfmiddlewaretoken", window.getCookie("csrftoken") ?? "")

        fetch(generateUrl, {
            method: "POST",
            body: formData,
            credentials: "same-origin",
            headers: {
                "X-CSRFToken": window.getCookie("csrftoken") ?? "",
            },
        })
            .then(async (response) => {
                const data = (await response.json()) as RegenerateResponse
                if (!response.ok || data.error) {
                    throw new Error(data.error ?? `HTTP error! status: ${response.status}`)
                }
                return data
            })
            .then((data) => {
                const url = data.temp_image_url ?? data.temp_audio_url
                tempFilename = data.temp_image_filename ?? data.temp_audio_filename ?? null
                if (!url || !tempFilename) {
                    throw new Error(gettext("No file was returned."))
                }
                renderNewPreview(url)
                newEmpty.classList.add("is-hidden")
                decision.classList.remove("is-hidden")
                generateButton.textContent = regenerateLabel
                showMessage(data.message ?? gettext("Generated!"), "success")
            })
            .catch((error: unknown) => {
                clearNew()
                showMessage(
                    `${gettext("Error")}: ${error instanceof Error ? error.message : String(error)}`,
                    "error",
                )
            })
            .finally(() => {
                setBusy(false)
            })
    })

    keepButton.addEventListener("click", () => {
        if (!tempFilename) {
            return
        }
        setBusy(true)
        showMessage(gettext("Saving..."), "")

        const formData = new FormData()
        formData.append(storeField, tempFilename)
        formData.append("csrfmiddlewaretoken", window.getCookie("csrftoken") ?? "")

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
                const data = (await response.json()) as { status?: string; message?: string }
                if (!response.ok || data.status !== "success") {
                    throw new Error(data.message ?? `HTTP error! status: ${response.status}`)
                }
                return data
            })
            .then(() => {
                // Reload so the saved value, check status and preview all refresh.
                window.location.reload()
            })
            .catch((error: unknown) => {
                showMessage(
                    `${gettext("Error")}: ${error instanceof Error ? error.message : String(error)}`,
                    "error",
                )
                setBusy(false)
            })
    })

    discardButton.addEventListener("click", () => {
        clearNew()
        generateButton.textContent = generateLabel
        showMessage("", "")
    })

    setBusy(false)
}

document.addEventListener("DOMContentLoaded", () => {
    document
        .querySelectorAll<HTMLElement>(".inline-regenerate")
        .forEach((widget) => _initRegenerateWidget(widget))
})
