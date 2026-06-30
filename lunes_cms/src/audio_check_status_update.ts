document.addEventListener("DOMContentLoaded", function () {
    const saveRow = document.querySelector<HTMLElement>(".submit-row")
    if (saveRow) {
        saveRow.style.display = "none"
    }

    const audioCheckStatusSelects = document.querySelectorAll<HTMLSelectElement>(
        ".audio-check-status-select",
    )

    audioCheckStatusSelects.forEach(function (select) {
        select.addEventListener("change", function () {
            const wordId = select.getAttribute("data-word-id")

            const csrftoken = window.getCookie("csrftoken")

            const formData = new FormData()
            formData.append("audio_check_status", select.value)

            fetch(`/en/admin/cmsv2/words/${wordId}/update-audio-check-status/`, {
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
                    alert("An error occurred while updating the audio check status")
                })
        })
    })
})
