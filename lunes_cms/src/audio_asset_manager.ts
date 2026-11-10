type AudioAssetManagerConfig = {
    entityType?: string
    assetType?: string
    containerClass?: string
    controlsClass?: string
    idAttribute?: string
    addBtnClass?: string
    replaceBtnClass?: string
    deleteBtnClass?: string
    fileInputClass?: string
    updateEndpoint?: string
    urlResponseKey?: string
    successMessages?: {
        update: string
        delete: string
    }
    errorMessages?: {
        update: string
        delete: string
    }
}

document.addEventListener("DOMContentLoaded", function () {
    const configs: AudioAssetManagerConfig[] = window.audioAssetManagerConfigs || []

    configs.forEach((config) => {
        const entityType = config.entityType || "entity"
        const assetType = config.assetType || "asset"
        const containerClass = config.containerClass || `${entityType}-${assetType}-container`
        const controlsClass = config.controlsClass || `${assetType}-controls`
        const idAttribute = config.idAttribute || `${entityType}Id`
        const addBtnClass = config.addBtnClass || `add-${assetType}-btn`
        const replaceBtnClass = config.replaceBtnClass || `replace-${assetType}-btn`
        const deleteBtnClass = config.deleteBtnClass || `delete-${assetType}-btn`
        const fileInputClass = config.fileInputClass || `${assetType}-file-input`
        const updateEndpoint =
            config.updateEndpoint || `/en/admin/cmsv2/${entityType}s/\${id}/update-${assetType}/`
        const errorMessages = config.errorMessages || {
            update: `An error occurred while updating the ${assetType}`,
            delete: `An error occurred while deleting the ${assetType}`,
        }

        document.querySelectorAll<HTMLElement>(`.${containerClass}`).forEach(function (container) {
            const controls = container.querySelector<HTMLElement>(`.${controlsClass}`)
            const entityId = controls?.dataset[idAttribute]
            // Rows can render their own endpoint, so it follows the language of the page.
            const endpoint =
                controls?.dataset.updateUrl ??
                (entityId ? updateEndpoint.replace("${id}", entityId) : undefined)
            const addBtn = container.querySelector<HTMLElement>(`.${addBtnClass}`)
            const replaceBtn = container.querySelector<HTMLElement>(`.${replaceBtnClass}`)
            const deleteBtn = container.querySelector<HTMLElement>(`.${deleteBtnClass}`)
            const fileInput = container.querySelector<HTMLInputElement>(`.${fileInputClass}`)

            if (addBtn) {
                addBtn.addEventListener("click", function () {
                    if (!fileInput) {
                        return
                    }
                    fileInput.click()
                    fileInput.dataset.action = "add"
                })
            }

            if (replaceBtn) {
                replaceBtn.addEventListener("click", function () {
                    if (!fileInput) {
                        return
                    }
                    fileInput.click()
                    fileInput.dataset.action = "replace"
                })
            }

            if (deleteBtn) {
                deleteBtn.addEventListener("click", function () {
                    if (confirm(`Are you sure you want to delete this ${assetType}?`)) {
                        deleteAsset(endpoint)
                    }
                })
            }

            if (fileInput) {
                fileInput.addEventListener("change", function () {
                    if (fileInput.files && fileInput.files.length > 0) {
                        uploadAsset(endpoint, fileInput.files[0], fileInput.dataset.action ?? "add")
                    }
                })
            }
        })

        function uploadAsset(endpoint: string | undefined, file: File, action: string): void {
            if (!endpoint) {
                console.error("Entity ID is missing")
                alert(errorMessages.update)
                return
            }

            const formData = new FormData()
            formData.append(assetType, file)
            formData.append("action", action)

            window
                .postWithCsrf(endpoint, formData)
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
                    alert(errorMessages.update)
                })
        }

        function deleteAsset(endpoint: string | undefined): void {
            if (!endpoint) {
                console.error("Entity ID is missing")
                alert(errorMessages.delete)
                return
            }

            const formData = new FormData()
            formData.append("action", "delete")

            window
                .postWithCsrf(endpoint, formData)
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
                    alert(errorMessages.delete)
                })
        }
    })
})
