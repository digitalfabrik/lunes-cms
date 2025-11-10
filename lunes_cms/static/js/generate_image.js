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

function initImageGenerator(config) {
    const generateButton = document.getElementById("generate_button")
    const regenerateButton = document.getElementById("regenerate_button")
    const storeButton = document.getElementById("store_button")
    const backButtons = document.querySelectorAll("a.button[href*='change']")

    const loadingSpinner = document.getElementById("loading_spinner")
    const messageArea = document.getElementById("message_area")
    const imagePreviewSection = document.getElementById("image_preview_section")
    const imagePreview = document.getElementById("image-preview")
    const tempFilenameDisplay = document.getElementById("temp_filename_display")
    const hiddenTempFilename = document.getElementById("hidden_temp_filename")

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
        messageArea.textContent = "Generating image..."
        messageArea.style.color = "inherit"
        imagePreviewSection.style.display = "none"
        imagePreview.style.display = "none"

        const formData = new FormData()
        if (config.formDataBuilder) {
            config.formDataBuilder(formData)
        }

        const inputElement = document.getElementById("prompt-additional-info")
        formData.append("additional_info", inputElement.value)
        const modelSelectElement = document.getElementById("model")
        formData.append("model", modelSelectElement.value)
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
        .catch(error => {
            console.error("Fetch error:", error)
            messageArea.textContent = `Network error: ${error.message}`
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
