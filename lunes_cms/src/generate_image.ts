type ImageGeneratorConfig = {
    generateUrl: string
    formDataBuilder?: (formData: FormData) => void
}

function _getImageCookie(name: string): string | null {
    let cookieValue: string | null = null
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

// Called from Django template (generate_image_base.html)
window.initImageGenerator = function (config: ImageGeneratorConfig): void {
    const generateButton = document.getElementById("generate_button") as HTMLButtonElement
    const regenerateButton = document.getElementById("regenerate_button") as HTMLButtonElement
    const storeButton = document.getElementById("store_button") as HTMLButtonElement
    const backButtons = document.querySelectorAll<HTMLAnchorElement>("a.button[href*='change']")

    const loadingSpinner = document.getElementById("loading_spinner") as HTMLElement
    const messageArea = document.getElementById("message_area") as HTMLElement
    const imagePreviewSection = document.getElementById("image_preview_section") as HTMLElement
    const imagePreview = document.getElementById("image-preview") as HTMLImageElement
    const tempFilenameDisplay = document.getElementById("temp_filename_display") as HTMLElement
    const hiddenTempFilename = document.getElementById("hidden_temp_filename") as HTMLInputElement

    function setButtonsState(generating: boolean): void {
        generateButton.disabled = generating
        regenerateButton.disabled = generating
        storeButton.disabled = generating
        if (generating) {
            backButtons.forEach((btn) => btn.classList.add("disabled"))
        } else {
            backButtons.forEach((btn) => btn.classList.remove("disabled"))
        }
    }

    function performGeneration(): void {
        setButtonsState(true)
        loadingSpinner.style.display = "inline-block"
        messageArea.textContent = "Generating image..."
        messageArea.style.color = "inherit"
        imagePreviewSection.style.display = "none"
        imagePreview.style.display = "none"

        const formData = new FormData()
        if (config.formDataBuilder) {
            config.formDataBuilder(formData)
        }

        const inputElement = document.getElementById("prompt-additional-info") as HTMLInputElement
        formData.append("additional_info", inputElement.value)
        formData.append("csrfmiddlewaretoken", _getImageCookie("csrftoken") ?? "")

        fetch(config.generateUrl, {
            method: "POST",
            body: formData,
            headers: {
                "X-CSRFToken": _getImageCookie("csrftoken") ?? "",
            },
        })
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`)
                }
                return response.json()
            })
            .then((data) => {
                if (data.error) {
                    messageArea.textContent = `Error: ${data.error}`
                    messageArea.style.color = "red"
                    imagePreviewSection.style.display = "none"
                    imagePreview.style.display = "none"
                } else {
                    messageArea.textContent = data.message
                    messageArea.style.color = "green"
                    imagePreviewSection.style.display = "block"
                    imagePreview.style.display = "block"
                    imagePreview.src = data.temp_image_url
                    tempFilenameDisplay.textContent = data.temp_image_filename
                    hiddenTempFilename.value = data.temp_image_filename
                }
            })
            .catch((error) => {
                console.error("Fetch error:", error)
                messageArea.textContent = `Network error: ${error instanceof Error ? error.message : String(error)}`
                messageArea.style.color = "red"
                imagePreview.style.display = "none"
            })
            .finally(() => {
                loadingSpinner.style.display = "none"
                setButtonsState(false)
            })
    }

    generateButton.addEventListener("click", performGeneration)
    regenerateButton.addEventListener("click", performGeneration)

    setButtonsState(false)
    regenerateButton.disabled = true
    storeButton.disabled = true
    imagePreviewSection.style.display = "none"
    imagePreview.style.display = "none"
}
