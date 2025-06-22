document.addEventListener("DOMContentLoaded", function() {
    const saveRow = document.querySelector(".submit-row");
    if (saveRow) {
        saveRow.style.display = "none";
    }

    // Word image check status selects
    const imageCheckStatusSelects = document.querySelectorAll(".image-check-status-select");

    imageCheckStatusSelects.forEach(function(select) {
        select.addEventListener("change", function() {
            const wordId = select.getAttribute("data-word-id");

            const csrftoken = getCookie("csrftoken");

            const formData = new FormData();
            formData.append("image_check_status", select.value);

            fetch(`/en/admin/cmsv2/words/${wordId}/update-image-check-status/`, {
                method: "POST",
                body: formData,
                headers: {
                    "X-CSRFToken": csrftoken
                },
                credentials: "same-origin"
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === "success") {
                    window.location.reload();
                } else {
                    alert(`Error: ${data.message}`);
                }
            })
            .catch(error => {
                console.error("Error:", error);
                alert("An error occurred while updating the image check status");
            });
        });
    });

    // UnitWord image check status selects
    const unitwordImageCheckStatusSelects = document.querySelectorAll(".unitword-image-check-status-select");

    unitwordImageCheckStatusSelects.forEach(function(select) {
        select.addEventListener("change", function() {
            const unitwordId = select.getAttribute("data-unitword-id");

            const csrftoken = getCookie("csrftoken");

            const formData = new FormData();
            formData.append("image_check_status", select.value);

            fetch(`/en/admin/cmsv2/unitwords/${unitwordId}/update-image-check-status/`, {
                method: "POST",
                body: formData,
                headers: {
                    "X-CSRFToken": csrftoken
                },
                credentials: "same-origin"
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === "success") {
                    window.location.reload();
                } else {
                    alert(`Error: ${data.message}`);
                }
            })
            .catch(error => {
                console.error("Error:", error);
                alert("An error occurred while updating the unit-word image check status");
            });
        });
    });

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== "") {
            const cookies = document.cookie.split(";");
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + "=")) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});