document.addEventListener("DOMContentLoaded", function () {
    const rowFields = [
        "alt_word",
        "grammatical_gender",
        "singular_article",
        "plural_article",
        "plural",
    ]

    function collectRowData(button: HTMLButtonElement): FormData {
        const formData = new FormData()
        const row = button.closest("tr")
        if (!row) {
            return formData
        }
        rowFields.forEach(function (field) {
            const input = row.querySelector<HTMLInputElement | HTMLSelectElement>(
                `[name$="-${field}"]`,
            )
            if (input) {
                formData.append(field, input.value)
            }
        })
        return formData
    }

    function postAlternativeWord(endpoint: string, formData: FormData, errorMessage: string) {
        const csrftoken = window.getCookie("csrftoken")

        fetch(endpoint, {
            method: "POST",
            body: formData,
            headers: {
                "X-CSRFToken": csrftoken ?? "",
            },
            credentials: "same-origin",
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.status === "success") {
                    window.location.reload()
                } else {
                    alert(`Error: ${data.message}`)
                }
            })
            .catch((error) => {
                console.error("Error:", error)
                alert(errorMessage)
            })
    }

    // The word id is only available on the change page, not on the add page
    const wordIdMatch = window.location.pathname.match(/\/word\/(\d+)\/change\//)

    document
        .querySelectorAll<HTMLButtonElement>(".add-alternative-word-btn")
        .forEach(function (button) {
            if (!wordIdMatch) {
                button.style.display = "none"
                return
            }
            button.addEventListener("click", function () {
                const formData = collectRowData(button)
                formData.append("word_id", wordIdMatch[1])
                postAlternativeWord(
                    "/en/admin/cmsv2/alternativewords/save/",
                    formData,
                    "An error occurred while adding the alternative word",
                )
            })
        })

    document
        .querySelectorAll<HTMLButtonElement>(".save-alternative-word-btn")
        .forEach(function (button) {
            button.addEventListener("click", function () {
                const alternativeWordId = button.getAttribute("data-alternative-word-id")
                if (!alternativeWordId) {
                    console.error("Alternative word ID is missing")
                    return
                }
                const formData = collectRowData(button)
                formData.append("alternative_word_id", alternativeWordId)
                postAlternativeWord(
                    "/en/admin/cmsv2/alternativewords/save/",
                    formData,
                    "An error occurred while saving the alternative word",
                )
            })
        })

    document
        .querySelectorAll<HTMLButtonElement>(".delete-alternative-word-btn")
        .forEach(function (button) {
            button.addEventListener("click", function () {
                const alternativeWordId = button.getAttribute("data-alternative-word-id")
                if (!alternativeWordId) {
                    console.error("Alternative word ID is missing")
                    return
                }
                postAlternativeWord(
                    `/en/admin/cmsv2/alternativewords/${alternativeWordId}/delete/`,
                    new FormData(),
                    "An error occurred while deleting the alternative word",
                )
            })
        })
})
