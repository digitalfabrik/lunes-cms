function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

document.addEventListener("DOMContentLoaded", function() {
    const configs = window.assetManagerConfigs || []

    configs.forEach(config => {
        const entityType = config.entityType || "entity"
        const assetType = config.assetType || "asset"
        const containerClass = config.containerClass || `${entityType}-${assetType}-container`
        const controlsClass = config.controlsClass || `${assetType}-controls`
        const idAttribute = config.idAttribute || `${entityType}Id`
        const addBtnClass = config.addBtnClass || `add-${assetType}-btn`
        const replaceBtnClass = config.replaceBtnClass || `replace-${assetType}-btn`
        const deleteBtnClass = config.deleteBtnClass || `delete-${assetType}-btn`
        const fileInputClass = config.fileInputClass || `${assetType}-file-input`
        const updateEndpoint = config.updateEndpoint || `/en/admin/cmsv2/${entityType}s/\${id}/update-${assetType}/`
        const errorMessages = config.errorMessages || {
            update: `An error occurred while updating the ${assetType}`,
            delete: `An error occurred while deleting the ${assetType}`
        }

        document.querySelectorAll(`.${containerClass}`).forEach(function(container) {
            const controls = container.querySelector(`.${controlsClass}`)
            const entityId = controls ? controls.dataset[idAttribute] || controls.getAttribute(`data-${idAttribute.replace(/([A-Z])/g, '-$1').toLowerCase()}`) : null
            const addBtn = container.querySelector(`.${addBtnClass}`)
            const replaceBtn = container.querySelector(`.${replaceBtnClass}`)
            const deleteBtn = container.querySelector(`.${deleteBtnClass}`)
            const fileInput = container.querySelector(`.${fileInputClass}`)

            if (addBtn) {
                addBtn.addEventListener("click", function() {
                    fileInput.click()
                    fileInput.dataset.action = "add"
                })
            }

            if (replaceBtn) {
                replaceBtn.addEventListener("click", function() {
                    fileInput.click()
                    fileInput.dataset.action = "replace"
                })
            }

            if (deleteBtn) {
                deleteBtn.addEventListener("click", function() {
                    if (confirm(`Are you sure you want to delete this ${assetType}?`)) {
                        deleteAsset(entityId)
                    }
                })
            }

            if (fileInput) {
                fileInput.addEventListener("change", function() {
                    if (fileInput.files.length > 0) {
                        uploadAsset(entityId, fileInput.files[0], fileInput.dataset.action)
                    }
                })
            }
        })

        function uploadAsset(entityId, file, action) {
            if (!entityId) {
                console.error("Entity ID is missing")
                alert(errorMessages.update)
                return
            }

            const formData = new FormData()
            formData.append(assetType, file)
            formData.append("action", action)

            const csrftoken = getCookie('csrftoken')

            const endpoint = updateEndpoint.replace("${id}", entityId)

            fetch(endpoint, {
                method: "POST",
                body: formData,
                credentials: "same-origin",
                headers: {
                    'X-CSRFToken': csrftoken
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === "success") {
                    window.location.reload()
                } else {
                    alert(`Error: ${data.message}`)
                }
            })
            .catch(error => {
                console.error("Error:", error)
                alert(errorMessages.update)
            })
        }

        function deleteAsset(entityId) {
            if (!entityId) {
                console.error("Entity ID is missing")
                alert(errorMessages.delete)
                return
            }

            const formData = new FormData()
            formData.append("action", "delete")

            const csrftoken = getCookie('csrftoken')

            const endpoint = updateEndpoint.replace("${id}", entityId)

            fetch(endpoint, {
                method: "POST",
                body: formData,
                credentials: "same-origin",
                headers: {
                    'X-CSRFToken': csrftoken
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === "success") {
                    window.location.reload()
                } else {
                    alert(`Error: ${data.message}`)
                }
            })
            .catch(error => {
                console.error("Error:", error)
                alert(errorMessages.delete)
            })
        }
    })
})
