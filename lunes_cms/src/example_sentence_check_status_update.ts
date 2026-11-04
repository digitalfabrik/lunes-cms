document.addEventListener("DOMContentLoaded", function () {
    const saveRow = document.querySelector<HTMLElement>(".submit-row")
    if (saveRow) {
        saveRow.style.display = "none"
    }

    const exampleSentenceCheckStatusSelects = document.querySelectorAll<HTMLSelectElement>(
        ".example-sentence-check-status-select",
    )

    exampleSentenceCheckStatusSelects.forEach(function (select) {
        select.addEventListener("change", function () {
            const url = select.dataset.url
            if (!url) {
                return
            }

            const formData = new FormData()
            formData.append("example_sentence_check_status", select.value)

            window
                .postWithCsrf(url, formData)
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
                    alert("An error occurred while updating the example sentence check status")
                })
        })
    })
})
