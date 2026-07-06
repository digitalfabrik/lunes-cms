type AudioGeneratorConfig = {
    textFieldName: string
    textValue: string
    generateUrl: string
}

// Called from Django template (generate_audio_base.html)
window.initAudioGenerator = function (config: AudioGeneratorConfig): void {
    const generateButton = document.getElementById("generate_button") as HTMLButtonElement
    const regenerateButton = document.getElementById("regenerate_button") as HTMLButtonElement
    const storeButton = document.getElementById("store_button") as HTMLButtonElement
    const backButtons = document.querySelectorAll<HTMLAnchorElement>("a.button[href*='change']")

    const loadingSpinner = document.getElementById("loading_spinner") as HTMLElement
    const messageArea = document.getElementById("message_area") as HTMLElement
    const audioPreviewSection = document.getElementById("audio_preview_section") as HTMLElement
    const audioPlayer = document.getElementById("audio_preview_player") as HTMLAudioElement
    const tempFilenameDisplay = document.getElementById("temp_filename_display") as HTMLElement
    const hiddenTempAudioFilename = document.getElementById(
        "hidden_temp_audio_filename",
    ) as HTMLInputElement

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
        messageArea.textContent = "Generating audio..."
        messageArea.style.color = "inherit"
        audioPreviewSection.style.display = "none"
        audioPlayer.src = ""

        const formData = new FormData()
        formData.append(config.textFieldName, config.textValue)
        formData.append("csrfmiddlewaretoken", window.getCookie("csrftoken") ?? "")

        fetch(config.generateUrl, {
            method: "POST",
            body: formData,
            headers: {
                "X-CSRFToken": window.getCookie("csrftoken") ?? "",
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
                    audioPreviewSection.style.display = "none"
                } else {
                    messageArea.textContent = data.message
                    messageArea.style.color = "green"
                    audioPlayer.src = data.temp_audio_url
                    tempFilenameDisplay.textContent = data.temp_audio_filename
                    hiddenTempAudioFilename.value = data.temp_audio_filename
                    audioPreviewSection.style.display = "block"
                }
            })
            .catch((error) => {
                console.error("Fetch error:", error)
                messageArea.textContent = `Network error: ${error instanceof Error ? error.message : String(error)}`
                messageArea.style.color = "red"
                audioPreviewSection.style.display = "none"
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
    audioPreviewSection.style.display = "none"

    audioPlayer.addEventListener("loadeddata", () => {
        regenerateButton.disabled = false
        storeButton.disabled = false
    })
}
