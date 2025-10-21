function getCookie(name) {
    let cookieValue = null
    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";")
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim()
            if (cookie.substring(0, name.length + 1) === (name + "=")) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1))
                break
            }
        }
    }
    return cookieValue
}

function initAudioGenerator(config) {
    const generateButton = document.getElementById("generate_button")
    const regenerateButton = document.getElementById("regenerate_button")
    const storeButton = document.getElementById("store_button")
    const backButtons = document.querySelectorAll("a.button[href*='change']")

    const loadingSpinner = document.getElementById("loading_spinner")
    const messageArea = document.getElementById("message_area")
    const audioPreviewSection = document.getElementById("audio_preview_section")
    const audioPlayer = document.getElementById("audio_preview_player")
    const tempFilenameDisplay = document.getElementById("temp_filename_display")
    const hiddenTempAudioFilename = document.getElementById("hidden_temp_audio_filename")

    let currentTempAudioFilename = null

    function setButtonsState(generating) {
        generateButton.disabled = generating
        regenerateButton.disabled = generating
        storeButton.disabled = generating
        if (generating) {
            backButtons.forEach(btn => btn.classList.add("disabled"))
        } else {
            backButtons.forEach(btn => btn.classList.remove("disabled"))
        }
    }

    function performGeneration() {
        setButtonsState(true)
        loadingSpinner.style.display = "inline-block"
        messageArea.textContent = "Generating audio..."
        messageArea.style.color = "inherit"
        audioPreviewSection.style.display = "none"
        audioPlayer.src = ""

        const formData = new FormData()
        formData.append(config.textFieldName, config.textValue)
        formData.append("csrfmiddlewaretoken", getCookie("csrftoken"))

        fetch(config.generateUrl, {
            method: "POST",
            body: formData,
            headers: {
                "X-CSRFToken": getCookie("csrftoken")
            },
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`)
            }
            return response.json()
        })
        .then(data => {
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
                currentTempAudioFilename = data.temp_audio_filename
            }
        })
        .catch(error => {
            console.error("Fetch error:", error)
            messageArea.textContent = `Network error: ${error.message}`
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
